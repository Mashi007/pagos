"""
Scheduler para tareas automáticas
Usa APScheduler para ejecutar tareas programadas
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler(daemon=True)


def calcular_notificaciones_previas_job():
    """Job que calcula y ENVÍA notificaciones previas a las 4 AM"""
    db = SessionLocal()
    try:
        from app.services.notificaciones_previas_service import NotificacionesPreviasService
        from app.services.email_service import EmailService
        from app.models.notificacion_plantilla import NotificacionPlantilla
        from app.models.notificacion import Notificacion
        from datetime import datetime

        logger.info("🔄 [Scheduler] Iniciando cálculo y envío de notificaciones previas...")

        # Calcular notificaciones previas
        service = NotificacionesPreviasService(db)
        resultados = service.calcular_notificaciones_previas()

        logger.info(
            f"📊 [Scheduler] Notificaciones previas calculadas: {len(resultados)} registros "
            f"(5 días: {len([r for r in resultados if r['dias_antes_vencimiento'] == 5])}, "
            f"3 días: {len([r for r in resultados if r['dias_antes_vencimiento'] == 3])}, "
            f"1 día: {len([r for r in resultados if r['dias_antes_vencimiento'] == 1])})"
        )

        # Inicializar servicio de email (carga configuración desde BD)
        email_service = EmailService(db=db)

        # Contadores
        enviadas = 0
        fallidas = 0
        sin_plantilla = 0
        sin_email = 0

        # Procesar cada notificación previa
        for resultado in resultados:
            cliente_id = resultado["cliente_id"]
            dias_antes = resultado["dias_antes_vencimiento"]
            correo_cliente = resultado["correo"]
            nombre_cliente = resultado["nombre"]
            monto_cuota = resultado["monto_cuota"]
            fecha_vencimiento = resultado["fecha_vencimiento"]
            numero_cuota = resultado["numero_cuota"]
            prestamo_id = resultado["prestamo_id"]

            # Determinar tipo de notificación según días
            tipo_notificacion = None
            if dias_antes == 5:
                tipo_notificacion = "PAGO_5_DIAS_ANTES"
            elif dias_antes == 3:
                tipo_notificacion = "PAGO_3_DIAS_ANTES"
            elif dias_antes == 1:
                tipo_notificacion = "PAGO_1_DIA_ANTES"

            if not tipo_notificacion:
                continue

            # Verificar que el cliente tenga email
            if not correo_cliente:
                logger.warning(f"⚠️ Cliente {cliente_id} no tiene email registrado, saltando...")
                sin_email += 1
                continue

            # Buscar plantilla activa para este tipo
            plantilla = (
                db.query(NotificacionPlantilla)
                .filter(NotificacionPlantilla.tipo == tipo_notificacion, NotificacionPlantilla.activa.is_(True))
                .first()
            )

            if not plantilla:
                logger.warning(f"⚠️ No hay plantilla activa para tipo {tipo_notificacion}, saltando cliente {cliente_id}...")
                sin_plantilla += 1
                continue

            # Reemplazar variables en plantilla
            asunto = plantilla.asunto
            cuerpo = plantilla.cuerpo

            # Variables disponibles
            variables = {
                "nombre": nombre_cliente,
                "monto": f"{monto_cuota:.2f}",
                "fecha_vencimiento": fecha_vencimiento,
                "numero_cuota": str(numero_cuota),
                "credito_id": str(prestamo_id),
                "cedula": resultado.get("cedula", ""),
            }

            for key, value in variables.items():
                asunto = asunto.replace(f"{{{{{key}}}}}", str(value))
                cuerpo = cuerpo.replace(f"{{{{{key}}}}}", str(value))

            # Crear registro de notificación
            nueva_notif = Notificacion(
                cliente_id=cliente_id,
                tipo=tipo_notificacion,
                canal="EMAIL",
                asunto=asunto,
                mensaje=cuerpo,
                estado="PENDIENTE",
            )
            db.add(nueva_notif)
            db.commit()
            db.refresh(nueva_notif)

            # Enviar email
            try:
                resultado_email = email_service.send_email(
                    to_emails=[str(correo_cliente)],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                )

                # Actualizar estado según resultado
                if resultado_email.get("success"):
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.utcnow()
                    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
                    enviadas += 1
                    logger.info(f"✅ Email enviado a {correo_cliente} (Cliente {cliente_id}, {dias_antes} días antes)")
                else:
                    nueva_notif.estado = "FALLIDA"
                    nueva_notif.error_mensaje = resultado_email.get("message", "Error desconocido")
                    nueva_notif.intentos = 1
                    fallidas += 1
                    logger.error(f"❌ Error enviando email a {correo_cliente}: {resultado_email.get('message')}")

                db.commit()

            except Exception as e:
                db.rollback()
                nueva_notif.estado = "FALLIDA"
                nueva_notif.error_mensaje = str(e)
                nueva_notif.intentos = 1
                db.commit()
                fallidas += 1
                logger.error(f"❌ Excepción enviando email a {correo_cliente}: {e}", exc_info=True)

        logger.info(
            f"✅ [Scheduler] Proceso completado: "
            f"{enviadas} enviadas, {fallidas} fallidas, {sin_plantilla} sin plantilla, {sin_email} sin email"
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en job de notificaciones previas: {e}", exc_info=True)
    finally:
        db.close()


def iniciar_scheduler():
    """Inicia el scheduler con todas las tareas programadas"""
    try:
        # Agregar job para notificaciones previas (4 AM diariamente)
        # Este job calcula las notificaciones previas Y ENVÍA los correos automáticamente
        scheduler.add_job(
            calcular_notificaciones_previas_job,
            trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
            id="notificaciones_previas",
            name="Calcular y Enviar Notificaciones Previas",
            replace_existing=True,
        )

        # Iniciar scheduler
        scheduler.start()
        logger.info("✅ Scheduler iniciado correctamente")
        logger.info("📅 Job 'notificaciones_previas' programado para ejecutarse diariamente a las 4:00 AM")
        logger.info(
            "📧 El job calculará notificaciones previas y enviará correos automáticamente usando plantillas y configuración de email"
        )

    except Exception as e:
        logger.error(f"❌ Error iniciando scheduler: {e}", exc_info=True)


def detener_scheduler():
    """Detiene el scheduler"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler detenido correctamente")
    except Exception as e:
        logger.error(f"❌ Error deteniendo scheduler: {e}", exc_info=True)
