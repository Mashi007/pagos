# -*- coding: utf-8 -*-
"""
Servicio de scheduler para ejecutar actualizacion de estado a LIQUIDADO a las 9 PM
con generación y envío de notificaciones con PDF adjunto.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from sqlalchemy import text
import logging
from datetime import datetime
from app.services.liquidado_notificacion_service import notificacion_service

logger = logging.getLogger(__name__)

class LiquidadoScheduler:
    def __init__(self):
        self.scheduler = None
    
    def actualizar_prestamos_liquidado(self):
        """Ejecuta la funcion que actualiza prestamos a LIQUIDADO y genera notificaciones"""
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
            
            # Generar notificaciones para cada prestamo liquidado
            logger.info('Iniciando generacion de notificaciones con PDF')
            notificaciones_exitosas = 0
            notificaciones_fallidas = 0
            
            for prestamo_id, capital, suma_pagado in prestamos_a_liquidar:
                try:
                    exito = notificacion_service.crear_notificacion(
                        prestamo_id=prestamo_id,
                        capital=float(capital or 0),
                        suma_pagado=float(suma_pagado or 0)
                    )
                    if exito:
                        notificaciones_exitosas += 1
                    else:
                        notificaciones_fallidas += 1
                except Exception as e:
                    logger.error(f'Error generando notificacion para prestamo {prestamo_id}: {e}')
                    notificaciones_fallidas += 1
            
            # Consultar total de cambios registrados
            cambios = db.execute(text('''
                SELECT COUNT(*) FROM auditoria_cambios_estado_prestamo
                WHERE DATE(fecha_cambio) = CURRENT_DATE
            ''')).fetchone()
            
            logger.info(f'COMPLETADO: {cambios[0]} prestamos actualizados a LIQUIDADO')
            logger.info(f'Notificaciones: {notificaciones_exitosas} exitosas, {notificaciones_fallidas} fallidas')
            
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
            name='Actualizacion diaria de prestamos a LIQUIDADO con notificaciones',
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
