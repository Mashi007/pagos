# -*- coding: utf-8 -*-
"""
Scheduler: actualizacion de estado a LIQUIDADO a las 21:00 (Caracas).

El correo con PDF de estado de cuenta NO se envia aqui: el job diario
liquidado_email_deferido (01:10) lo envia 1 y 2 dias calendario despues
segun prestamos.fecha_liquidado.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text, update

from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

class LiquidadoScheduler:
    def __init__(self):
        self.scheduler = None
    
    def actualizar_prestamos_liquidado(self):
        """Ejecuta la funcion que actualiza prestamos a LIQUIDADO y asigna fecha_liquidado (Caracas)."""
        db = SessionLocal()
        try:
            logger.info('INICIANDO: Actualizacion de prestamos a LIQUIDADO')
            
            # Obtener prestamos que van a ser liquidados (antes de actualizar)
            prestamos_a_liquidar = db.execute(text('''
                SELECT p.id, p.total_financiamiento, COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0)
                FROM prestamos p
                LEFT JOIN cuotas c ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                GROUP BY p.id, p.total_financiamiento
                HAVING COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= p.total_financiamiento - 0.01
            ''')).fetchall()
            
            logger.info(f'Se encontraron {len(prestamos_a_liquidar)} prestamos para liquidar')
            
            # Ejecutar funcion que actualiza estados
            result = db.execute(text('''
                SELECT actualizar_prestamos_a_liquidado_automatico()
            ''')).fetchone()
            
            db.commit()

            ids_liquidados = [row[0] for row in prestamos_a_liquidar]
            if ids_liquidados:
                fd = hoy_negocio()
                db.execute(
                    update(Prestamo)
                    .where(Prestamo.id.in_(ids_liquidados))
                    .values(fecha_liquidado=fd)
                )
                db.commit()
                logger.info(
                    "fecha_liquidado=%s asignada a %s prestamos (emails PDF dias siguientes via job 01:10)",
                    fd,
                    len(ids_liquidados),
                )

            # Consultar total de cambios registrados
            cambios = db.execute(text('''
                SELECT COUNT(*) FROM auditoria_cambios_estado_prestamo
                WHERE DATE(fecha_cambio) = CURRENT_DATE
            ''')).fetchone()
            
            logger.info(f'COMPLETADO: {cambios[0]} prestamos actualizados a LIQUIDADO')
            
        except Exception as e:
            logger.error(f'ERROR en actualizar_prestamos_liquidado: {e}', exc_info=True)
            try:
                db.rollback()
            except:
                pass
        finally:
            db.close()
    
    def iniciar_scheduler(self):
        """Inicia el scheduler"""
        self.scheduler = BackgroundScheduler()
        
        # Configurar job a las 9 PM (21:00) todos los dias
        self.scheduler.add_job(
            self.actualizar_prestamos_liquidado,
            'cron',
            hour=21,
            minute=0,
            id='actualizar_liquidado_diario',
            name='Actualizacion diaria de prestamos a LIQUIDADO (sin email; email 01:10)',
            misfire_grace_time=60
        )
        
        self.scheduler.start()
        logger.info('Scheduler iniciado. Job programado para las 21:00 (9 PM) diariamente')
    
    def detener_scheduler(self):
        """Detiene el scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info('Scheduler detenido')


# Instancia global del scheduler
liquidado_scheduler = LiquidadoScheduler()
