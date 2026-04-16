# -*- coding: utf-8 -*-
"""
Scheduler: actualizacion de estado a LIQUIDADO a las 21:00 (Caracas).

El correo automatico por liquidacion (PDF estado de cuenta) fue retirado del scheduler.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text, update

from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio
from app.services.prestamo_db_compat import prestamos_tiene_columna_fecha_liquidado

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
            if ids_liquidados and prestamos_tiene_columna_fecha_liquidado(db):
                fd = hoy_negocio()
                db.execute(
                    update(Prestamo)
                    .where(Prestamo.id.in_(ids_liquidados))
                    .values(fecha_liquidado=fd)
                )
                db.commit()
                logger.info(
                    "fecha_liquidado=%s asignada a %s prestamos",
                    fd,
                    len(ids_liquidados),
                )
            elif ids_liquidados:
                logger.warning(
                    "Omitido UPDATE fecha_liquidado: columna no existe (aplique migracion 023)."
                )

            if ids_liquidados:
                try:
                    from app.services.finiquito_refresh import (
                        refrescar_finiquito_caso_prestamo_si_aplica,
                    )

                    for lid in ids_liquidados:
                        refrescar_finiquito_caso_prestamo_si_aplica(db, int(lid))
                    db.commit()
                except Exception:
                    logger.exception(
                        "Error refrescando finiquito_casos tras batch LIQUIDADO (n=%s)",
                        len(ids_liquidados),
                    )
                    try:
                        db.rollback()
                    except Exception:
                        pass

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
            name='Actualizacion diaria de prestamos a LIQUIDADO',
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
