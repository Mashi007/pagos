"""
Script de reconciliación de pagos con cuotas
Soluciona el problema crítico de pagos no vinculados a cuotas
"""

import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote_plus

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ✅ CORRECCIÓN: Manejar encoding de DATABASE_URL antes de importar SessionLocal
# Si DATABASE_URL tiene caracteres especiales, codificarlos correctamente
database_url = os.getenv("DATABASE_URL")
if database_url:
    try:
        # Intentar decodificar como UTF-8 (si es bytes, convertir a string)
        if isinstance(database_url, bytes):
            # Si es bytes, intentar decodificar con diferentes encodings
            try:
                database_url = database_url.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    database_url = database_url.decode('latin-1')
                except UnicodeDecodeError:
                    database_url = database_url.decode('cp1252', errors='ignore')
        
        # Verificar si la URL tiene caracteres que necesitan encoding
        # Parsear y reconstruir la URL con encoding correcto
        if '@' in database_url and '://' in database_url:
            # Separar protocolo, credenciales y resto
            protocol_part = database_url.split('://')[0]
            rest_part = database_url.split('://')[1]
            
            if '@' in rest_part:
                auth_part, host_part = rest_part.split('@', 1)
                if ':' in auth_part:
                    user, password = auth_part.split(':', 1)
                    # Codificar contraseña usando quote_plus
                    password_encoded = quote_plus(password, safe='')
                    database_url = f"{protocol_part}://{user}:{password_encoded}@{host_part}"
                    os.environ["DATABASE_URL"] = database_url
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ No se pudo procesar DATABASE_URL para encoding: {e}")
        # Continuar con la URL original

from sqlalchemy import or_

from app.db.session import SessionLocal
from app.models.amortizacion import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.utils.pagos_cuotas_helper import reconciliar_pago_cuota

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reconciliar_pagos_cuotas(dry_run: bool = True):
    """
    Reconcilia pagos con cuotas usando múltiples estrategias.
    
    Args:
        dry_run: Si True, solo muestra lo que haría sin hacer cambios
    """
    db = SessionLocal()
    
    try:
        # 1. Pagos con prestamo_id y numero_cuota - verificar que la cuota existe
        pagos_con_info = db.query(Pago).filter(
            Pago.activo == True,
            Pago.prestamo_id.isnot(None),
            Pago.numero_cuota.isnot(None)
        ).all()
        
        logger.info(f"📊 Encontrados {len(pagos_con_info)} pagos con prestamo_id y numero_cuota")
        
        reconciliados_estrategia1 = 0
        for pago in pagos_con_info:
            cuota = db.query(Cuota).filter(
                Cuota.prestamo_id == pago.prestamo_id,
                Cuota.numero_cuota == pago.numero_cuota
            ).first()
            
            if cuota:
                # Actualizar total_pagado de la cuota
                if cuota.total_pagado is None:
                    cuota.total_pagado = Decimal("0")
                
                if not dry_run:
                    cuota.total_pagado += pago.monto_pagado
                    
                    # Actualizar estado si está completamente pagada
                    if cuota.total_pagado >= cuota.monto_cuota:
                        cuota.estado = "PAGADO"
                        if not cuota.fecha_pago:
                            cuota.fecha_pago = pago.fecha_pago.date()
                
                reconciliados_estrategia1 += 1
            else:
                logger.warning(
                    f"⚠️ Pago {pago.id}: Cuota no encontrada "
                    f"(prestamo_id={pago.prestamo_id}, numero_cuota={pago.numero_cuota})"
                )
        
        logger.info(f"✅ Estrategia 1: {reconciliados_estrategia1} pagos reconciliados")
        
        # 2. Pagos sin prestamo_id o numero_cuota - intentar reconciliar por cédula y fecha
        pagos_sin_info = db.query(Pago).filter(
            Pago.activo == True,
            or_(Pago.prestamo_id.is_(None), Pago.numero_cuota.is_(None))
        ).all()
        
        logger.info(f"📊 Encontrados {len(pagos_sin_info)} pagos sin prestamo_id o numero_cuota")
        
        reconciliados_estrategia2 = 0
        for pago in pagos_sin_info:
            cuota = reconciliar_pago_cuota(db, pago)
            
            if cuota:
                # Actualizar total_pagado
                if cuota.total_pagado is None:
                    cuota.total_pagado = Decimal("0")
                
                if not dry_run:
                    cuota.total_pagado += pago.monto_pagado
                    
                    if cuota.total_pagado >= cuota.monto_cuota:
                        cuota.estado = "PAGADO"
                        if not cuota.fecha_pago:
                            cuota.fecha_pago = pago.fecha_pago.date()
                
                reconciliados_estrategia2 += 1
        
        logger.info(f"✅ Estrategia 2: {reconciliados_estrategia2} pagos reconciliados")
        
        # 3. Corregir cuotas marcadas como PAGADO pero sin pagos
        cuotas_pagadas = db.query(Cuota).join(
            Prestamo, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Cuota.estado == "PAGADO",
            Prestamo.estado == "APROBADO"
        ).all()
        
        logger.info(f"📊 Verificando {len(cuotas_pagadas)} cuotas marcadas como PAGADO")
        
        corregidas = 0
        for cuota in cuotas_pagadas:
            prestamo = db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
            if not prestamo:
                continue
            
            # Buscar pagos usando helper
            from app.utils.pagos_cuotas_helper import obtener_pagos_cuota
            
            pagos = obtener_pagos_cuota(
                db=db,
                prestamo_id=cuota.prestamo_id,
                numero_cuota=cuota.numero_cuota,
                cedula=prestamo.cedula,
                fecha_vencimiento=cuota.fecha_vencimiento,
                monto_cuota=cuota.monto_cuota
            )
            
            if not pagos:
                # No hay pagos, cambiar estado
                if not dry_run:
                    cuota.estado = "PENDIENTE"
                    cuota.fecha_pago = None
                corregidas += 1
            else:
                # Hay pagos, verificar que sumen al menos monto_cuota
                total_pagado = sum(p.monto_pagado for p in pagos)
                if total_pagado < cuota.monto_cuota:
                    if not dry_run:
                        cuota.estado = "PARCIAL" if total_pagado > 0 else "PENDIENTE"
                elif cuota.total_pagado != total_pagado:
                    # Actualizar total_pagado
                    if not dry_run:
                        cuota.total_pagado = total_pagado
        
        logger.info(f"✅ Cuotas corregidas: {corregidas}")
        
        if not dry_run:
            db.commit()
            logger.info("✅ Cambios guardados en la base de datos")
        else:
            logger.info("🔍 DRY RUN: No se hicieron cambios. Ejecutar con dry_run=False para aplicar cambios.")
        
        return {
            "reconciliados_estrategia1": reconciliados_estrategia1,
            "reconciliados_estrategia2": reconciliados_estrategia2,
            "cuotas_corregidas": corregidas,
            "total_reconciliados": reconciliados_estrategia1 + reconciliados_estrategia2
        }
        
    except Exception as e:
        logger.error(f"❌ Error en reconciliación: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reconciliar pagos con cuotas")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios (por defecto es dry-run)"
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 Iniciando reconciliación de pagos con cuotas...")
    resultado = reconciliar_pagos_cuotas(dry_run=not args.apply)
    
    logger.info("=" * 80)
    logger.info("📊 RESUMEN DE RECONCILIACIÓN")
    logger.info("=" * 80)
    logger.info(f"✅ Pagos reconciliados (Estrategia 1): {resultado['reconciliados_estrategia1']}")
    logger.info(f"✅ Pagos reconciliados (Estrategia 2): {resultado['reconciliados_estrategia2']}")
    logger.info(f"✅ Cuotas corregidas: {resultado['cuotas_corregidas']}")
    logger.info(f"✅ Total reconciliados: {resultado['total_reconciliados']}")
    logger.info("=" * 80)

