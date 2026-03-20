# -*- coding: utf-8 -*-
"`"
Script de diagnóstico y corrección de problemas críticos de conciliación.

Problemas a resolver:
1. 14,127 pagos sin asignar a cuotas (3,426,096.76 BS = 49.2%)
2. 1 cuota sobre-aplicada (Cuota 216933: 96 BS exceso)
3. Estados inconsistentes (MORA no documentado)
"`"
import logging
from decimal import Decimal
from datetime import datetime
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiagnosticoCritico:
    "`"Diagnóstico de problemas críticos"`"

    @staticmethod
    def diagnosticar_pagos_sin_asignar(db: Session) -> dict:
        "`"Diagnostica los 14,127 pagos sin asignar"`"
        
        # Pagos sin cuotas asignadas
        pagos_sin_asignar = db.query(text('''
            SELECT 
              p.id,
              p.cedula,
              p.prestamo_id,
              p.fecha_pago,
              p.monto_pagado,
              p.referencia_pago,
              p.estado,
              EXTRACT(DAY FROM NOW() - p.fecha_pago::TIMESTAMP) as dias_sin_asignar,
              pr.cedula as cedula_cliente,
              pr.nombre as nombre_cliente
            FROM pagos p
            LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
            WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
            ORDER BY p.fecha_pago ASC
        ''')).fetchall()
        
        logger.info(f'Total pagos sin asignar: {len(pagos_sin_asignar)}')
        
        # Análisis por categoría
        pagos_nuevos = [p for p in pagos_sin_asignar if p[7] < 7]  # < 7 días
        pagos_antiguos = [p for p in pagos_sin_asignar if 7 <= p[7] < 30]  # 7-30 días
        pagos_muy_antiguos = [p for p in pagos_sin_asignar if p[7] >= 30]  # > 30 días
        
        pagos_sin_prestamo = [p for p in pagos_sin_asignar if p[2] is None]
        
        monto_total = sum([Decimal(str(p[4])) for p in pagos_sin_asignar])
        
        return {
            'total_pagos': len(pagos_sin_asignar),
            'monto_total': float(monto_total),
            'pagos_recientes': len(pagos_nuevos),
            'pagos_antiguos_7_30': len(pagos_antiguos),
            'pagos_muy_antiguos': len(pagos_muy_antiguos),
            'pagos_sin_prestamo': len(pagos_sin_prestamo),
            'lista_pagos': [
                {
                    'id': p[0],
                    'cedula': p[1],
                    'prestamo_id': p[2],
                    'fecha_pago': p[3].isoformat() if p[3] else None,
                    'monto': float(p[4]),
                    'referencia': p[5],
                    'estado': p[6],
                    'dias_sin_asignar': p[7],
                    'cedula_cliente': p[8],
                    'nombre_cliente': p[9]
                }
                for p in pagos_sin_asignar[:100]  # Primeros 100 para no saturar
            ]
        }

    @staticmethod
    def diagnosticar_cuota_sobre_aplicada(db: Session, cuota_id: int = 216933) -> dict:
        "`"Diagnostica la cuota 216933 sobre-aplicada"`"
        
        cuota_data = db.query(text('''
            SELECT 
              c.id,
              c.prestamo_id,
              c.numero_cuota,
              c.monto,
              c.estado,
              c.fecha_vencimiento,
              COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado,
              COALESCE(SUM(cp.monto_aplicado), 0) - c.monto as exceso,
              COUNT(cp.id) as num_pagos
            FROM cuotas c
            LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
            WHERE c.id = :cuota_id
            GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto, c.estado, c.fecha_vencimiento
        '''), {'cuota_id': cuota_id}).fetchone()
        
        if not cuota_data:
            return {'error': f'Cuota {cuota_id} no encontrada'}
        
        # Obtener detalles de pagos aplicados
        detalles_pagos = db.query(text('''
            SELECT 
              cp.pago_id,
              cp.monto_aplicado,
              p.cedula,
              p.fecha_pago,
              p.referencia_pago,
              cp.fecha_aplicacion
            FROM cuota_pagos cp
            JOIN pagos p ON cp.pago_id = p.id
            WHERE cp.cuota_id = :cuota_id
            ORDER BY cp.fecha_aplicacion
        '''), {'cuota_id': cuota_id}).fetchall()
        
        logger.warning(f'Cuota {cuota_id} sobre-aplicada: {cuota_data[7]} BS exceso')
        
        return {
            'cuota_id': cuota_data[0],
            'prestamo_id': cuota_data[1],
            'numero_cuota': cuota_data[2],
            'monto_cuota': float(cuota_data[3]),
            'estado': cuota_data[4],
            'fecha_vencimiento': cuota_data[5].isoformat() if cuota_data[5] else None,
            'total_aplicado': float(cuota_data[6]),
            'exceso': float(cuota_data[7]),
            'num_pagos': cuota_data[8],
            'pagos_aplicados': [
                {
                    'pago_id': p[0],
                    'monto': float(p[1]),
                    'cedula': p[2],
                    'fecha_pago': p[3].isoformat() if p[3] else None,
                    'referencia': p[4],
                    'fecha_aplicacion': p[5].isoformat() if p[5] else None
                }
                for p in detalles_pagos
            ]
        }

    @staticmethod
    def diagnosticar_estados_inconsistentes(db: Session) -> dict:
        "`"Diagnostica inconsistencias en estados de cuota"`"
        
        # Cuotas en estado MORA pero calculado diferente
        cuotas_mora = db.query(text('''
            SELECT 
              c.id,
              c.prestamo_id,
              c.numero_cuota,
              c.monto,
              c.estado,
              c.fecha_vencimiento,
              c.dias_mora,
              COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado,
              CASE 
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE'
              END as estado_calculado,
              EXTRACT(DAY FROM NOW() - c.fecha_vencimiento::TIMESTAMP) as dias_vencida
            FROM cuotas c
            LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
            WHERE c.estado = 'MORA'
            GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto, c.estado, 
                     c.fecha_vencimiento, c.dias_mora
            LIMIT 100
        ''')).fetchall()
        
        inconsistencias = [
            {
                'cuota_id': c[0],
                'prestamo_id': c[1],
                'numero_cuota': c[2],
                'estado_registrado': c[4],
                'estado_calculado': c[8],
                'coincide': c[4] == c[8],
                'dias_mora': c[6],
                'dias_vencida': c[9],
                'total_aplicado': float(c[7]),
                'monto': float(c[3])
            }
            for c in cuotas_mora if c[4] != c[8]  # Solo mostrar inconsistencias
        ]
        
        logger.warning(f'Inconsistencias detectadas: {len(inconsistencias)}')
        
        return {
            'total_mora': len(cuotas_mora),
            'inconsistencias': len(inconsistencias),
            'detalle': inconsistencias[:20]
        }


class CorrectoresCriticos:
    "`"Correctores automáticos para problemas críticos"`"

    @staticmethod
    def corregir_cuota_sobre_aplicada(db: Session, cuota_id: int = 216933):
        "`"Corrige la cuota 216933 reduciendo el monto del último pago aplicado"`"
        
        try:
            # Obtener exceso
            exceso_data = db.query(text('''
                SELECT 
                  COALESCE(SUM(cp.monto_aplicado), 0) - c.monto as exceso
                FROM cuotas c
                LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
                WHERE c.id = :cuota_id
                GROUP BY c.monto
            '''), {'cuota_id': cuota_id}).fetchone()
            
            if not exceso_data or exceso_data[0] <= 0:
                logger.info(f'Cuota {cuota_id} no tiene exceso')
                return {'success': False, 'message': 'No hay exceso'}
            
            exceso = Decimal(str(exceso_data[0]))
            
            # Obtener el último pago aplicado
            ultimo_pago = db.query(text('''
                SELECT cp.id, cp.pago_id, cp.monto_aplicado
                FROM cuota_pagos cp
                WHERE cp.cuota_id = :cuota_id
                ORDER BY cp.fecha_aplicacion DESC
                LIMIT 1
            '''), {'cuota_id': cuota_id}).fetchone()
            
            if not ultimo_pago:
                return {'success': False, 'message': 'No hay pagos para corregir'}
            
            # Reducir el último pago por el exceso
            nuevo_monto = Decimal(str(ultimo_pago[2])) - exceso
            
            db.execute(text('''
                UPDATE cuota_pagos
                SET monto_aplicado = :nuevo_monto
                WHERE id = :cp_id
            '''), {'nuevo_monto': nuevo_monto, 'cp_id': ultimo_pago[0]})
            
            # Registrar en auditoría
            db.execute(text('''
                INSERT INTO auditoria_conciliacion_manual 
                (pago_id, cuota_id, monto_asignado, tipo_asignacion, resultado, motivo)
                VALUES (:pago_id, :cuota_id, :monto, 'MANUAL', 'EXITOSA', :motivo)
            '''), {
                'pago_id': ultimo_pago[1],
                'cuota_id': cuota_id,
                'monto': exceso,
                'motivo': f'Corrección de sobre-aplicación: reducción de {exceso}'
            })
            
            db.commit()
            logger.info(f'Cuota {cuota_id} corregida: reducido {exceso} BS del último pago')
            
            return {
                'success': True,
                'message': f'Cuota corregida: exceso {float(exceso)} BS revertido',
                'cuota_id': cuota_id,
                'exceso_corregido': float(exceso)
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f'Error corrigiendo cuota: {e}')
            return {'success': False, 'error': str(e)}

    @staticmethod
    def corregir_estados_mora_inconsistentes(db: Session):
        "`"Corrige estados MORA que no coinciden con cálculo"`"
        
        try:
            # Actualizar cuotas con estado incorrecto
            result = db.execute(text('''
                WITH cuotas_calculo AS (
                  SELECT 
                    c.id,
                    CASE 
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                      WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                      ELSE 'PENDIENTE'
                    END as estado_correcto
                  FROM cuotas c
                  LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
                  WHERE c.estado = 'MORA'
                  GROUP BY c.id, c.monto, c.fecha_vencimiento
                )
                UPDATE cuotas c
                SET estado = cc.estado_correcto
                FROM cuotas_calculo cc
                WHERE c.id = cc.id AND c.estado != cc.estado_correcto
            '''))
            
            db.commit()
            logger.info(f'Estados corregidos: {result.rowcount} cuotas actualizadas')
            
            return {
                'success': True,
                'message': f'{result.rowcount} cuotas actualizadas con estado correcto',
                'cuotas_actualizadas': result.rowcount
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f'Error corrigiendo estados: {e}')
            return {'success': False, 'error': str(e)}
