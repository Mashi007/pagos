# -*- coding: utf-8 -*-
\"\"\"
Servicio de scheduler para ejecutar actualizacion de estado a LIQUIDADO a las 9 PM
\"\"\"
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LiquidadoScheduler:
    def __init__(self):
        self.scheduler = None
    
    def actualizar_prestamos_liquidado(self):
        \"\"\"Ejecuta la funcion que actualiza prestamos a LIQUIDADO\"\"\"
        db = SessionLocal()
        try:
            logger.info('INICIANDO: Actualizacion de prestamos a LIQUIDADO')
            
            # Ejecutar funcion
            result = db.execute(text('''
                SELECT actualizar_prestamos_a_liquidado_automatico()
            ''')).fetchone()
            
            # Consultar cambios registrados
            cambios = db.execute(text('''
                SELECT COUNT(*) FROM auditoria_cambios_estado_prestamo
                WHERE DATE(fecha_cambio) = CURRENT_DATE
            ''')).fetchone()
            
            logger.info(f'COMPLETADO: {cambios[0]} prestamos actualizados a LIQUIDADO hoy')
            
            db.commit()
        except Exception as e:
            logger.error(f'ERROR en actualizar_prestamos_liquidado: {e}')
            db.rollback()
        finally:
            db.close()
    
    def iniciar_scheduler(self):
        \"\"\"Inicia el scheduler\"\"\"
        self.scheduler = BackgroundScheduler()
        
        # Configurar job a las 9 PM (21:00) todos los dias
        self.scheduler.add_job(
            self.actualizar_prestamos_liquidado,
            'cron',
            hour=21,
            minute=0,
            id='actualizar_liquidado_diario',
            name='Actualizacion diaria de prestamos a LIQUIDADO',
            misfire_grace_time=60
        )
        
        self.scheduler.start()
        logger.info('Scheduler iniciado. Job programado para las 21:00 (9 PM)')
    
    def detener_scheduler(self):
        \"\"\"Detiene el scheduler\"\"\"
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info('Scheduler detenido')

# Instancia global
liquidado_scheduler = LiquidadoScheduler()
