# Crear servicio de notificacion para prestamos LIQUIDADO

contenido = '''# -*- coding: utf-8 -*-
\"\"\"
Servicio de notificaciones para prestamos LIQUIDADO
Se dispara automaticamente cuando se actualiza el estado a LIQUIDADO
\"\"\"

from app.core.database import SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class LiquidadoNotificacionService:
    \"\"\"Servicio que crea notificaciones cuando se actualizan prestamos a LIQUIDADO\"\"\"
    
    @staticmethod
    def crear_notificacion_prestamo_liquidado(prestamo_id: int, total_financiamiento: float, suma_pagado: float):
        \"\"\"
        Crea un registro de notificacion cuando un prestamo se marca como LIQUIDADO.
        Esta notificacion aparecera en la pestaña de notificaciones del frontend.
        \"\"\"
        db = SessionLocal()
        try:
            logger.info(f'Creando notificacion para prestamo_id={prestamo_id} LIQUIDADO')
            
            # 1. Obtener datos del prestamo y cliente
            result = db.execute(text('''
                SELECT 
                    p.id,
                    p.cliente_id,
                    c.email,
                    c.cedula,
                    p.referencia_interna,
                    p.total_financiamiento
                FROM prestamos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                WHERE p.id = :prestamo_id
            '''), {'prestamo_id': prestamo_id}).fetchone()
            
            if not result:
                logger.warning(f'Prestamo {prestamo_id} no encontrado para crear notificacion')
                return False
            
            prestamo_id_v, cliente_id, email, cedula, ref_interna, capital = result
            
            # 2. Crear evento en tabla de notificaciones/auditoria
            # Usar tipo = 'liquidado' para identificar en frontend
            db.execute(text('''
                INSERT INTO envio_notificacion 
                    (prestamo_id, cliente_id, cedula, email, tipo, asunto, cuerpo, exito, fecha_envio)
                VALUES 
                    (:prestamo_id, :cliente_id, :cedula, :email, :tipo, :asunto, :cuerpo, :exito, NOW())
            '''), {
                'prestamo_id': prestamo_id,
                'cliente_id': cliente_id,
                'cedula': cedula or '',
                'email': email or '',
                'tipo': 'liquidado',  # Nueva categoria
                'asunto': f'Prestamo {ref_interna} - 100% Liquidado',
                'cuerpo': f'Su prestamo por {total_financiamiento:.2f} ha sido liquidado exitosamente. Capital pagado: {suma_pagado:.2f}',
                'exito': True
            })
            db.commit()
            
            logger.info(f'Notificacion creada exitosamente para prestamo_id={prestamo_id}')
            return True
            
        except Exception as e:
            logger.error(f'Error al crear notificacion de LIQUIDADO: {e}')
            db.rollback()
            return False
        finally:
            db.close()

# Instancia global
notificacion_service = LiquidadoNotificacionService()
'''

with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\services\liquidado_notificacion_service.py', 'w', encoding='utf-8') as f:
    f.write(contenido)

print('[OK] Servicio de notificaciones de LIQUIDADO creado')
