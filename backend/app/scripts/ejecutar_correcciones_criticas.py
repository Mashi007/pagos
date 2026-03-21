# -*- coding: utf-8 -*-
"""
Script de automatización para ejecutar correcciones críticas.
Puede ser usado como CLI o importado como módulo.
"""
import sys
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.cuota_estado import SQL_PG_ESTADO_CUOTA_CASE_CORRELATED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomatizadorCriticos:
    """Automatiza la ejecución de correcciones críticas"""

    @staticmethod
    def ejecutar_todas_correcciones(db: Session, dry_run: bool = True) -> dict:
        resultado = {
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': dry_run,
            'correcciones': {}
        }

        try:
            logger.info('=' * 80)
            logger.info('CORRECCIÓN 1: Asignando pagos sin cuotas')
            logger.info('=' * 80)
            
            resultado['correcciones']['asignacion_pagos'] = \
                AutomatizadorCriticos._corregir_pagos_sin_asignar(db, dry_run)
            
            logger.info('=' * 80)
            logger.info('CORRECCIÓN 2: Corrigiendo cuota 216933')
            logger.info('=' * 80)
            
            resultado['correcciones']['cuota_sobre_aplicada'] = \
                AutomatizadorCriticos._corregir_cuota_216933(db, dry_run)
            
            logger.info('=' * 80)
            logger.info('CORRECCIÓN 3: Actualizando estados')
            logger.info('=' * 80)
            
            resultado['correcciones']['estados_inconsistentes'] = \
                AutomatizadorCriticos._corregir_estados(db, dry_run)
            
            if not dry_run:
                db.commit()
                logger.info('✓ TODAS LAS CORRECCIONES CONFIRMADAS EN BD')
            else:
                db.rollback()
                logger.info('ℹ DRY RUN COMPLETADO')
            
            return resultado

        except Exception as e:
            logger.error(f'ERROR: {e}', exc_info=True)
            db.rollback()
            resultado['error'] = str(e)
            return resultado

    @staticmethod
    def _corregir_pagos_sin_asignar(db: Session, dry_run: bool) -> dict:
        pagos_sin_asignar = db.query(text('''
            SELECT COUNT(*), COALESCE(SUM(monto_pagado), 0)
            FROM pagos p
            WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
        ''')).fetchone()
        
        logger.info(f'Pagos sin asignar: {pagos_sin_asignar[0]} ({pagos_sin_asignar[1]} BS)')
        
        if dry_run:
            return {
                'status': 'dry_run',
                'pagos_encontrados': pagos_sin_asignar[0],
                'monto': float(pagos_sin_asignar[1])
            }
        
        result = db.execute(text('''
            INSERT INTO cuota_pagos (cuota_id, pago_id, monto_aplicado, orden_aplicacion)
            SELECT c.id, p.id, LEAST(p.monto_pagado, c.monto_cuota - COALESCE((
                SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id
              ), 0)), 1
            FROM pagos p
            JOIN clientes cl ON p.cedula = cl.cedula
            JOIN prestamos pr ON cl.id = pr.cliente_id AND pr.estado = 'APROBADO'
            JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')
            WHERE p.prestamo_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
        '''))
        
        logger.info(f'✓ {result.rowcount} asignaciones creadas')
        return {'status': 'success', 'asignaciones_creadas': result.rowcount}

    @staticmethod
    def _corregir_cuota_216933(db: Session, dry_run: bool) -> dict:
        exceso_data = db.query(text('''
            SELECT COALESCE(SUM(cp.monto_aplicado), 0) - c.monto_cuota
            FROM cuotas c LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
            WHERE c.id = 216933 GROUP BY c.monto_cuota
        ''')).fetchone()
        
        if not exceso_data or exceso_data[0] <= Decimal('0.01'):
            logger.info('ℹ Cuota sin exceso significativo')
            return {'status': 'no_action', 'exceso': 0}
        
        exceso = Decimal(str(exceso_data[0]))
        logger.info(f'Exceso: {exceso} BS')
        
        if dry_run:
            return {'status': 'dry_run', 'exceso': float(exceso)}
        
        ultimo_pago = db.query(text('''
            SELECT cp.id, cp.monto_aplicado
            FROM cuota_pagos cp WHERE cp.cuota_id = 216933
            ORDER BY cp.fecha_aplicacion DESC LIMIT 1
        ''')).fetchone()
        
        nuevo_monto = Decimal(str(ultimo_pago[1])) - exceso
        db.execute(text('''
            UPDATE cuota_pagos SET monto_aplicado = :nuevo_monto WHERE id = :cp_id
        '''), {'nuevo_monto': nuevo_monto, 'cp_id': ultimo_pago[0]})
        
        logger.info(f'✓ Cuota corregida: {exceso} BS revertido')
        return {'status': 'success', 'exceso_corregido': float(exceso)}

    @staticmethod
    def _corregir_estados(db: Session, dry_run: bool) -> dict:
        inconsistencias = db.query(text('''
            SELECT COUNT(*) FROM cuotas c
            WHERE c.estado NOT IN (
              'PAGADO', 'PAGO_ADELANTADO', 'PARCIAL', 'VENCIDO',
              'MORA', 'PENDIENTE', 'CANCELADA'
            )
        ''')).fetchone()
        
        total_inconsistencias = inconsistencias[0] if inconsistencias else 0
        logger.info(f'Inconsistencias: {total_inconsistencias}')
        
        if dry_run:
            return {'status': 'dry_run', 'inconsistencias': total_inconsistencias}
        
        case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
        result = db.execute(
            text(
                "UPDATE cuotas c SET estado = ("
                + case_sql
                + ") WHERE c.estado IS DISTINCT FROM ("
                + case_sql
                + ")"
            )
        )
        
        logger.info(f'✓ {result.rowcount} cuotas actualizadas')
        return {'status': 'success', 'cuotas_actualizadas': result.rowcount}
