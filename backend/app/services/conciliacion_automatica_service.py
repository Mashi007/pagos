# -*- coding: utf-8 -*-
"""
Servicio de conciliaciÃ³n automÃ¡tica de pagos no conciliados.

CaracterÃ­sticas:
1. Asigna automÃ¡ticamente pagos sin cuotas a cuotas pendientes (FIFO)
2. Valida en tiempo real para evitar sobre-aplicaciones
3. Registra auditorÃ­a de cada asignaciÃ³n
4. Genera alertas de pagos problemÃ¡ticos
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy import and_, desc, text, func
from sqlalchemy.orm import Session
import logging

from app.models.pago import Pago
from app.models.cuota import Cuota
from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio
from app.models.cuota_pago import CuotaPago
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


class EstadoCuota:
    """Estados vÃ¡lidos de una cuota con documentaciÃ³n."""
    PAGADO = 'PAGADO'
    PENDIENTE = 'PENDIENTE'
    VENCIDO = 'VENCIDO'
    MORA = 'MORA'
    PARCIAL = 'PARCIAL'
    PAGO_ADELANTADO = 'PAGO_ADELANTADO'
    CANCELADA = 'CANCELADA'
    
    ESTADOS_VALIDOS = {PAGADO, PENDIENTE, VENCIDO, MORA, PARCIAL, PAGO_ADELANTADO, CANCELADA}
    
    DOCUMENTACION = {
        PAGADO: 'Cuota cubierta al 100% (vencimiento ya cumplido o hoy).',
        PENDIENTE: 'Sin cubrir al 100%; al corriente (vencimiento hoy o futuro).',
        VENCIDO: 'Sin cubrir al 100%; 1 a 91 dias despues del vencimiento.',
        MORA: 'Sin cubrir al 100%; 92 o mas dias despues del vencimiento.',
        PARCIAL: 'Abonos sin cubrir al 100%; aun al corriente respecto al vencimiento.',
        PAGO_ADELANTADO: 'Cubierta al 100% antes de la fecha de vencimiento.',
        CANCELADA: 'Cuota anulada o no vigente. No requiere pago.',
    }

    @classmethod
    def obtener_documentacion(cls, estado: str) -> str:
        return cls.DOCUMENTACION.get(estado, f'Estado desconocido: {estado}')


class ValidadorSobreAplicacion:
    """Valida en tiempo real para evitar sobre-aplicaciones de pagos."""

    @staticmethod
    def obtener_monto_aplicado_actual(db: Session, cuota_id: int) -> Decimal:
        result = db.query(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)).filter(
            CuotaPago.cuota_id == cuota_id
        ).scalar()
        return Decimal(str(result)) if result else Decimal('0')

    @staticmethod
    def validar_aplicacion(
        db: Session,
        cuota: Cuota,
        monto_a_aplicar: Decimal
    ) -> Tuple[bool, List[str]]:
        errores = []
        
        monto_aplicado = ValidadorSobreAplicacion.obtener_monto_aplicado_actual(db, cuota.id)
        monto_total_permitido = Decimal(str(cuota.monto or 0))
        
        if monto_aplicado + monto_a_aplicar > monto_total_permitido + Decimal('0.01'):
            errores.append(
                f'Sobre-aplicaciÃ³n: {monto_aplicado} + {monto_a_aplicar} > {monto_total_permitido}'
            )
        
        if monto_a_aplicar <= 0:
            errores.append(f'Monto debe ser positivo: {monto_a_aplicar}')
        
        if cuota.estado == EstadoCuota.CANCELADA:
            errores.append(f'No se puede aplicar a cuota cancelada (id={cuota.id})')
        
        return (len(errores) == 0, errores)

    @staticmethod
    def calcular_estado_actualizado(db: Session, cuota_id: int) -> str:
        cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            return EstadoCuota.PENDIENTE

        monto_aplicado = ValidadorSobreAplicacion.obtener_monto_aplicado_actual(db, cuota_id)
        monto_total_f = float(cuota.monto or 0)
        total_pagado_f = float(monto_aplicado)
        fv = cuota.fecha_vencimiento
        fv_d = fv.date() if fv and hasattr(fv, "date") else fv
        return clasificar_estado_cuota(total_pagado_f, monto_total_f, fv_d, hoy_negocio())


class ConciliacionAutomaticaService:
    """Servicio principal de conciliaciÃ³n automÃ¡tica."""

    @staticmethod
    def asignar_pagos_no_conciliados(
        db: Session,
        prestamo_id: int = None,
        cliente_id: int = None,
        usuario_id: int = None
    ) -> Dict:
        resultado = {
            'exitosas': 0,
            'fallidas': 0,
            'total_monto_asignado': Decimal('0'),
            'asignaciones': [],
            'errores': []
        }

        try:
            query_pagos = db.query(Pago).outerjoin(
                CuotaPago, Pago.id == CuotaPago.pago_id
            ).filter(CuotaPago.id == None)
            
            if prestamo_id:
                query_pagos = query_pagos.filter(Pago.prestamo_id == prestamo_id)
            
            pagos_sin_asignar = query_pagos.order_by(Pago.fecha_pago).all()
            
            logger.info(f'Encontrados {len(pagos_sin_asignar)} pagos sin asignar')

            for pago in pagos_sin_asignar:
                saldo_pago = Decimal(str(pago.monto_pagado or 0))
                
                if saldo_pago <= 0:
                    continue
                
                if not pago.prestamo_id:
                    resultado['errores'].append(
                        f'Pago {pago.id}: No tiene prestamo_id asignado.'
                    )
                    resultado['fallidas'] += 1
                    continue
                
                cuotas_pendientes = db.query(Cuota).filter(
                    and_(
                        Cuota.prestamo_id == pago.prestamo_id,
                        Cuota.estado.in_([EstadoCuota.PENDIENTE, EstadoCuota.VENCIDO, EstadoCuota.MORA, EstadoCuota.PARCIAL])
                    )
                ).order_by(Cuota.numero_cuota).all()
                
                for cuota in cuotas_pendientes:
                    if saldo_pago <= 0:
                        break
                    
                    monto_a_aplicar = min(
                        saldo_pago,
                        Decimal(str(cuota.monto or 0))
                    )
                    
                    es_valido, errores_validacion = ValidadorSobreAplicacion.validar_aplicacion(
                        db, cuota, monto_a_aplicar
                    )
                    
                    if not es_valido:
                        resultado['errores'].append(
                            f'Pago {pago.id} -> Cuota {cuota.id}: {", ".join(errores_validacion)}'
                        )
                        resultado['fallidas'] += 1
                        continue
                    
                    cuota_pago = CuotaPago(
                        cuota_id=cuota.id,
                        pago_id=pago.id,
                        monto_aplicado=monto_a_aplicar,
                        orden_aplicacion=1
                    )
                    db.add(cuota_pago)
                    
                    saldo_pago -= monto_a_aplicar
                    resultado['exitosas'] += 1
                    resultado['total_monto_asignado'] += monto_a_aplicar
                    resultado['asignaciones'].append({
                        'pago_id': pago.id,
                        'cuota_id': cuota.id,
                        'monto': float(monto_a_aplicar)
                    })
                
                if saldo_pago > Decimal('0.01'):
                    resultado['errores'].append(
                        f'Pago {pago.id}: Sobra {saldo_pago} sin asignar.'
                    )
            
            db.commit()
            logger.info(
                f"Conciliación: {resultado['exitosas']} exitosas, "
                f"{resultado['fallidas']} fallidas. Total: {resultado['total_monto_asignado']}"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f'Error en conciliaciÃ³n: {e}', exc_info=True)
            resultado['errores'].append(f'Error fatal: {str(e)}')

        return resultado

    @staticmethod
    def obtener_resumen_estado_cuotas(db: Session) -> Dict:
        resultado = {}
        
        for estado in EstadoCuota.ESTADOS_VALIDOS:
            cantidad = db.query(func.count(Cuota.id)).filter(
                Cuota.estado == estado
            ).scalar() or 0
            
            monto_total = db.query(func.sum(Cuota.monto)).filter(
                Cuota.estado == estado
            ).scalar() or Decimal('0')
            
            resultado[estado] = {
                'cantidad': cantidad,
                'monto_total': float(monto_total),
                'documentacion': EstadoCuota.obtener_documentacion(estado)
            }
        
        return resultado

    @staticmethod
    def obtener_cuotas_sobre_aplicadas(db: Session) -> List[Dict]:
        resultado = []
        
        cuotas_problematicas = db.query(
            Cuota.id,
            Cuota.prestamo_id,
            Cuota.numero_cuota,
            Cuota.monto,
            func.sum(CuotaPago.monto_aplicado).label('total_aplicado')
        ).outerjoin(
            CuotaPago, Cuota.id == CuotaPago.cuota_id
        ).group_by(
            Cuota.id, Cuota.prestamo_id, Cuota.numero_cuota, Cuota.monto
        ).having(
            func.sum(CuotaPago.monto_aplicado) > Cuota.monto + Decimal('0.01')
        ).all()
        
        for cuota in cuotas_problematicas:
            resultado.append({
                'cuota_id': cuota[0],
                'prestamo_id': cuota[1],
                'numero_cuota': cuota[2],
                'monto_cuota': float(cuota[3]),
                'total_aplicado': float(cuota[4]),
                'exceso': float(cuota[4] - cuota[3])
            })
        
        return resultado

