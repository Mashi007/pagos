#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Job background para aplicar pagos pendientes a cuotas.
Ejecuta cada 5 minutos para procesar pagos sin aplicar.
"""
import logging
from decimal import Decimal
from sqlalchemy import and_, func, text

from app.core.database import SessionLocal
from app.models.pago import Pago
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago

logger = logging.getLogger(__name__)

# Lote maximo por corrida para acelerar sin perder calidad de validaciones.
BATCH_SIZE = 200
# Lock global en PostgreSQL para evitar ejecuciones concurrentes entre workers/instancias.
JOB_LOCK_KEY = 931337


def aplicar_pagos_pendientes():
    """
    Busca pagos no aplicados en lotes y los aplica a cuotas.
    """
    db = SessionLocal()
    lock_acquired = False
    try:
        # Evita que dos workers ejecuten el mismo job al mismo tiempo.
        lock_acquired = bool(db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": JOB_LOCK_KEY}).scalar())
        if not lock_acquired:
            logger.info("Job omitido: otra instancia ya esta aplicando pagos pendientes")
            return {"procesados": 0, "exitosos": 0, "errores": 0, "omitido_por_lock": 1}

        # Tomar lote de pagos sin aplicar (orden estable por antiguedad)
        pagos_sin_aplicar = (
            db.query(Pago)
            .outerjoin(CuotaPago, Pago.id == CuotaPago.pago_id)
            .filter(CuotaPago.id == None)
            .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
            .with_for_update(skip_locked=True)
            .limit(BATCH_SIZE)
            .all()
        )
        
        if not pagos_sin_aplicar:
            logger.info("Ningún pago pendiente por aplicar")
            return {"procesados": 0, "exitosos": 0, "errores": 0}
        
        logger.info(f"Encontrados {len(pagos_sin_aplicar)} pagos sin aplicar (lote max {BATCH_SIZE})")
        
        exitosos = 0
        errores = 0
        sin_cuotas = 0
        
        for pago in pagos_sin_aplicar:
            try:
                # Validar que tiene prestamo
                if not pago.prestamo_id:
                    logger.warning(f"Pago {pago.id}: Sin prestamo_id asignado")
                    errores += 1
                    continue
                
                saldo_pago = Decimal(str(pago.monto_pagado or 0))
                if saldo_pago <= 0:
                    logger.warning(f"Pago {pago.id}: Monto inválido ({saldo_pago})")
                    errores += 1
                    continue
                
                # Buscar cuotas pendientes del préstamo
                cuotas = db.query(Cuota).filter(
                    and_(
                        Cuota.prestamo_id == pago.prestamo_id,
                        Cuota.estado.in_(['PENDIENTE', 'MORA', 'PARCIAL'])
                    )
                ).order_by(Cuota.numero_cuota).all()
                
                if not cuotas:
                    logger.info(f"Pago {pago.id}: Préstamo {pago.prestamo_id} sin cuotas pendientes")
                    errores += 1
                    continue
                
                # Aplicar FIFO
                for cuota in cuotas:
                    if saldo_pago <= Decimal('0.01'):
                        break
                    
                    # Obtener monto ya aplicado
                    aplicado_existente = db.query(
                        func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)
                    ).filter(CuotaPago.cuota_id == cuota.id).scalar()
                    aplicado_existente = Decimal(str(aplicado_existente))
                    
                    # Calcular cuánto falta
                    monto_cuota = Decimal(str(cuota.monto or 0))
                    saldo_cuota = monto_cuota - aplicado_existente
                    
                    if saldo_cuota <= 0:
                        continue
                    
                    # Aplicar
                    monto_a_aplicar = min(saldo_pago, saldo_cuota)
                    
                    cuota_pago = CuotaPago(
                        cuota_id=cuota.id,
                        pago_id=pago.id,
                        monto_aplicado=monto_a_aplicar,
                        orden_aplicacion=1
                    )
                    db.add(cuota_pago)
                    saldo_pago -= monto_a_aplicar
                
                # Actualizar estado del pago si se aplicó completamente
                if saldo_pago < Decimal('0.01'):
                    pago.estado = 'PAGADO'
                elif saldo_pago < pago.monto_pagado:
                    pago.estado = 'PARCIAL'
                
                db.commit()
                exitosos += 1
                logger.info(f"Pago {pago.id}: Aplicado exitosamente")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error aplicando pago {pago.id}: {e}", exc_info=True)
                errores += 1
        
        logger.info(f"Job completado: {exitosos} exitosos, {sin_cuotas} sin cuotas, {errores} errores de {len(pagos_sin_aplicar)} totales")
        return {
            "procesados": len(pagos_sin_aplicar),
            "exitosos": exitosos,
            "errores": errores,
            "sin_cuotas": sin_cuotas
        }
        
    except Exception as e:
        logger.error(f"Error en job de aplicación de pagos: {e}", exc_info=True)
        return {"procesados": 0, "exitosos": 0, "errores": 1}
    finally:
        try:
            if lock_acquired:
                # Si la transaccion quedo abortada, limpiar antes de unlock.
                db.rollback()
                db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": JOB_LOCK_KEY})
        except Exception:
            logger.warning("No se pudo liberar advisory lock del job", exc_info=True)
        db.close()


if __name__ == "__main__":
    # Para ejecutar manualmente
    resultado = aplicar_pagos_pendientes()
    print(f"Resultado: {resultado}")
