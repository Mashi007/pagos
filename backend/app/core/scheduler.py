"""
Scheduler para tareas automáticas
Usa APScheduler para ejecutar tareas programadas
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import SessionLocal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler(daemon=True)


def _verificar_envio_habilitado(db: "Session", tipo_notificacion: str) -> bool:
    """Verificar si el envío de un tipo de notificación está habilitado"""
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        clave = f"envio_habilitado_{tipo_notificacion}"
        config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "NOTIFICACIONES",
                ConfiguracionSistema.clave == clave,
            )
            .first()
        )
        # Por defecto, todos habilitados (true)
        if not config or not config.valor:
            return True
        return config.valor.lower() in ("true", "1", "yes", "on")
    except Exception as e:
        logger.warning(f"⚠️ Error verificando habilitación para {tipo_notificacion}: {e}")
        return True  # Por defecto habilitado si hay error


def _obtener_cco_configurados(db: "Session", tipo_notificacion: str) -> List[str]:
    """Obtener lista de correos CCO configurados para un tipo de notificación"""
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        cco_emails = []
        for i in range(1, 4):  # CCO 1, 2, 3
            clave_cco = f"cco_{tipo_notificacion}_{i}"
            config_cco = (
                db.query(ConfiguracionSistema)
                .filter(
                    ConfiguracionSistema.categoria == "NOTIFICACIONES",
                    ConfiguracionSistema.clave == clave_cco,
                )
                .first()
            )
            if config_cco and config_cco.valor and config_cco.valor.strip():
                cco_emails.append(config_cco.valor.strip())
        
        return cco_emails
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo CCO para {tipo_notificacion}: {e}")
        return []


def _obtener_delay_envio(db: "Session") -> float:
    """Obtener delay configurado entre envíos (en segundos)"""
    try:
        from app.models.configuracion_sistema import ConfiguracionSistema
        
        clave = "delay_envio_email_segundos"
        config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "NOTIFICACIONES",
                ConfiguracionSistema.clave == clave,
            )
            .first()
        )
        # Por defecto, 2 segundos entre cada envío para evitar colisiones
        if config and config.valor:
            try:
                return float(config.valor)
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Valor inválido para delay_envio_email_segundos: {config.valor}, usando 2 segundos por defecto")
        return 2.0  # 2 segundos por defecto
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo delay de envío: {e}, usando 2 segundos por defecto")
        return 2.0


def calcular_notificaciones_previas_job():
    """Job que calcula y ENVÍA notificaciones previas a las 4 AM"""
    db = SessionLocal()
    try:
        from datetime import datetime

        from app.models.notificacion import Notificacion
        from app.models.notificacion_plantilla import NotificacionPlantilla
        from app.services.email_service import EmailService
        from app.services.notificaciones_previas_service import NotificacionesPreviasService
        from app.services.variables_notificacion_service import VariablesNotificacionService

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

        # Inicializar servicio de email con reutilización de conexión para envíos masivos
        email_service = EmailService(db=db, reuse_connection=True)

        # Contadores
        enviadas = 0
        fallidas = 0
        sin_plantilla = 0
        sin_email = 0

        # Inicializar servicio de variables
        variables_service = VariablesNotificacionService(db=db)

        # Obtener delay configurado entre envíos
        delay_envio = _obtener_delay_envio(db)
        logger.info(f"⏱️ Delay configurado entre envíos: {delay_envio} segundos")

        # Procesar cada notificación previa con delays para evitar colisiones
        total_resultados = len(resultados)
        import time
        
        for indice, resultado in enumerate(resultados, 1):
            # Delay entre cada envío para evitar colisiones (excepto el primero)
            if indice > 1:
                time.sleep(delay_envio)
            
            # Log de progreso cada 10 emails
            if indice % 10 == 0:
                logger.info(f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)")
            cliente_id = resultado["cliente_id"]
            dias_antes = resultado["dias_antes_vencimiento"]
            correo_cliente = resultado.get("correo", "")
            # El campo puede ser "nombre_cliente" o "nombre" según la query
            nombre_cliente = resultado.get("nombre_cliente", resultado.get("nombre", ""))
            monto_cuota = resultado.get("monto_cuota", 0)
            fecha_vencimiento = resultado.get("fecha_vencimiento", "")
            numero_cuota = resultado.get("numero_cuota", "")
            prestamo_id = resultado.get("prestamo_id", "")

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

            # Verificar si el envío está habilitado
            if not _verificar_envio_habilitado(db, tipo_notificacion):
                logger.info(f"⏸️ Envío de {tipo_notificacion} está deshabilitado, saltando cliente {cliente_id}...")
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

            # Construir variables desde el resultado de la query usando las variables configuradas
            variables = variables_service.construir_variables_desde_dict(
                datos_query=resultado,
            )

            # Reemplazar variables en plantilla usando el servicio
            asunto = variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables)
            cuerpo = variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables)

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

            # Obtener CCO configurados para este tipo
            cco_emails = _obtener_cco_configurados(db, tipo_notificacion)

            # Enviar email
            try:
                resultado_email = email_service.send_email(
                    to_emails=[str(correo_cliente)],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                    bcc_emails=cco_emails if cco_emails else None,
                )

                # Actualizar estado según resultado
                if resultado_email.get("success"):
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.utcnow()
                    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
                    enviadas += 1
                    cco_info = f" (CCO: {', '.join(cco_emails)})" if cco_emails else ""
                    logger.info(f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, {dias_antes} días antes)")
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
        # Cerrar conexión SMTP reutilizada
        try:
            email_service.close_connection()
        except:
            pass
        db.close()


def calcular_notificaciones_dia_pago_job():
    """Job que calcula y ENVÍA notificaciones del día de pago a las 4 AM"""
    db = SessionLocal()
    try:
        from datetime import datetime

        from app.models.notificacion import Notificacion
        from app.models.notificacion_plantilla import NotificacionPlantilla
        from app.services.email_service import EmailService
        from app.services.notificaciones_dia_pago_service import NotificacionesDiaPagoService
        from app.services.variables_notificacion_service import VariablesNotificacionService

        logger.info("🔄 [Scheduler] Iniciando cálculo y envío de notificaciones del día de pago...")

        # Calcular notificaciones del día de pago
        service = NotificacionesDiaPagoService(db)
        resultados = service.calcular_notificaciones_dia_pago()

        logger.info(f"📊 [Scheduler] Notificaciones del día de pago calculadas: {len(resultados)} registros")

        # Inicializar servicio de email con reutilización de conexión para envíos masivos
        email_service = EmailService(db=db, reuse_connection=True)

        # Contadores
        enviadas = 0
        fallidas = 0
        sin_plantilla = 0
        sin_email = 0

        # Inicializar servicio de variables
        variables_service = VariablesNotificacionService(db=db)

        # Obtener delay configurado entre envíos
        delay_envio = _obtener_delay_envio(db)
        logger.info(f"⏱️ Delay configurado entre envíos: {delay_envio} segundos")

        # Procesar cada notificación con delays para evitar colisiones
        total_resultados = len(resultados)
        import time
        
        for indice, resultado in enumerate(resultados, 1):
            # Delay entre cada envío para evitar colisiones (excepto el primero)
            if indice > 1:
                time.sleep(delay_envio)
            
            # Log de progreso cada 10 emails
            if indice % 10 == 0:
                logger.info(f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)")
            
            cliente_id = resultado["cliente_id"]
            correo_cliente = resultado.get("correo", "")
            tipo_notificacion = "PAGO_DIA_0"

            # Verificar si el envío está habilitado
            if not _verificar_envio_habilitado(db, tipo_notificacion):
                logger.info(f"⏸️ Envío de {tipo_notificacion} está deshabilitado, saltando cliente {cliente_id}...")
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

            # Construir variables desde el resultado
            variables = variables_service.construir_variables_desde_dict(datos_query=resultado)

            # Reemplazar variables en plantilla
            asunto = variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables)
            cuerpo = variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables)

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

            # Obtener CCO configurados para este tipo
            cco_emails = _obtener_cco_configurados(db, tipo_notificacion)

            # Enviar email
            try:
                resultado_email = email_service.send_email(
                    to_emails=[str(correo_cliente)],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                    bcc_emails=cco_emails if cco_emails else None,
                )

                if resultado_email.get("success"):
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.utcnow()
                    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
                    enviadas += 1
                    cco_info = f" (CCO: {', '.join(cco_emails)})" if cco_emails else ""
                    logger.info(f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, Día de pago)")
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
            f"✅ [Scheduler] Día de pago completado: "
            f"{enviadas} enviadas, {fallidas} fallidas, {sin_plantilla} sin plantilla, {sin_email} sin email"
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en job de día de pago: {e}", exc_info=True)
    finally:
        # Cerrar conexión SMTP reutilizada
        try:
            email_service.close_connection()
        except:
            pass
        db.close()


def calcular_notificaciones_retrasadas_job():
    """Job que calcula y ENVÍA notificaciones retrasadas a las 4 AM"""
    db = SessionLocal()
    try:
        from datetime import datetime

        from app.models.notificacion import Notificacion
        from app.models.notificacion_plantilla import NotificacionPlantilla
        from app.services.email_service import EmailService
        from app.services.notificaciones_retrasadas_service import NotificacionesRetrasadasService
        from app.services.variables_notificacion_service import VariablesNotificacionService

        logger.info("🔄 [Scheduler] Iniciando cálculo y envío de notificaciones retrasadas...")

        # Calcular notificaciones retrasadas
        service = NotificacionesRetrasadasService(db)
        resultados = service.calcular_notificaciones_retrasadas()

        logger.info(
            f"📊 [Scheduler] Notificaciones retrasadas calculadas: {len(resultados)} registros "
            f"(1 día: {len([r for r in resultados if r.get('dias_atrasado') == 1])}, "
            f"3 días: {len([r for r in resultados if r.get('dias_atrasado') == 3])}, "
            f"5 días: {len([r for r in resultados if r.get('dias_atrasado') == 5])})"
        )

        # Inicializar servicio de email con reutilización de conexión para envíos masivos
        email_service = EmailService(db=db, reuse_connection=True)

        # Contadores
        enviadas = 0
        fallidas = 0
        sin_plantilla = 0
        sin_email = 0

        # Inicializar servicio de variables
        variables_service = VariablesNotificacionService(db=db)

        # Obtener delay configurado entre envíos
        delay_envio = _obtener_delay_envio(db)
        logger.info(f"⏱️ Delay configurado entre envíos: {delay_envio} segundos")

        # Procesar cada notificación con delays para evitar colisiones
        total_resultados = len(resultados)
        import time
        
        for indice, resultado in enumerate(resultados, 1):
            # Delay entre cada envío para evitar colisiones (excepto el primero)
            if indice > 1:
                time.sleep(delay_envio)
            
            # Log de progreso cada 10 emails
            if indice % 10 == 0:
                logger.info(f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)")
            
            cliente_id = resultado["cliente_id"]
            dias_atrasado = resultado.get("dias_atrasado", 0)
            correo_cliente = resultado.get("correo", "")

            # Determinar tipo de notificación según días
            tipo_notificacion = None
            if dias_atrasado == 1:
                tipo_notificacion = "PAGO_1_DIA_ATRASADO"
            elif dias_atrasado == 3:
                tipo_notificacion = "PAGO_3_DIAS_ATRASADO"
            elif dias_atrasado == 5:
                tipo_notificacion = "PAGO_5_DIAS_ATRASADO"

            if not tipo_notificacion:
                continue

            # Verificar si el envío está habilitado
            if not _verificar_envio_habilitado(db, tipo_notificacion):
                logger.info(f"⏸️ Envío de {tipo_notificacion} está deshabilitado, saltando cliente {cliente_id}...")
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

            # Construir variables desde el resultado
            variables = variables_service.construir_variables_desde_dict(datos_query=resultado)

            # Reemplazar variables en plantilla
            asunto = variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables)
            cuerpo = variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables)

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

            # Obtener CCO configurados para este tipo
            cco_emails = _obtener_cco_configurados(db, tipo_notificacion)

            # Enviar email
            try:
                resultado_email = email_service.send_email(
                    to_emails=[str(correo_cliente)],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                    bcc_emails=cco_emails if cco_emails else None,
                )

                if resultado_email.get("success"):
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.utcnow()
                    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
                    enviadas += 1
                    cco_info = f" (CCO: {', '.join(cco_emails)})" if cco_emails else ""
                    logger.info(f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, {dias_atrasado} días atrasado)")
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
            f"✅ [Scheduler] Retrasadas completado: "
            f"{enviadas} enviadas, {fallidas} fallidas, {sin_plantilla} sin plantilla, {sin_email} sin email"
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en job de notificaciones retrasadas: {e}", exc_info=True)
    finally:
        # Cerrar conexión SMTP reutilizada
        try:
            email_service.close_connection()
        except:
            pass
        db.close()


def calcular_notificaciones_prejudiciales_job():
    """Job que calcula y ENVÍA notificaciones prejudiciales a las 4 AM"""
    db = SessionLocal()
    try:
        from datetime import datetime

        from app.models.notificacion import Notificacion
        from app.models.notificacion_plantilla import NotificacionPlantilla
        from app.services.email_service import EmailService
        from app.services.notificaciones_prejudicial_service import NotificacionesPrejudicialService
        from app.services.variables_notificacion_service import VariablesNotificacionService

        logger.info("🔄 [Scheduler] Iniciando cálculo y envío de notificaciones prejudiciales...")

        # Calcular notificaciones prejudiciales
        service = NotificacionesPrejudicialService(db)
        resultados = service.calcular_notificaciones_prejudiciales()

        logger.info(f"📊 [Scheduler] Notificaciones prejudiciales calculadas: {len(resultados)} registros")

        # Inicializar servicio de email con reutilización de conexión para envíos masivos
        email_service = EmailService(db=db, reuse_connection=True)

        # Contadores
        enviadas = 0
        fallidas = 0
        sin_plantilla = 0
        sin_email = 0

        # Inicializar servicio de variables
        variables_service = VariablesNotificacionService(db=db)

        # Obtener delay configurado entre envíos
        delay_envio = _obtener_delay_envio(db)
        logger.info(f"⏱️ Delay configurado entre envíos: {delay_envio} segundos")

        # Procesar cada notificación (solo una por cliente para evitar duplicados)
        clientes_procesados = set()
        tipo_notificacion = "PREJUDICIAL"
        
        # Procesar con delays para evitar colisiones
        total_resultados = len(resultados)
        import time
        
        for indice, resultado in enumerate(resultados, 1):
            cliente_id = resultado["cliente_id"]
            correo_cliente = resultado.get("correo", "")

            # Evitar enviar múltiples correos al mismo cliente
            if cliente_id in clientes_procesados:
                continue
            clientes_procesados.add(cliente_id)
            
            # Delay entre cada envío para evitar colisiones (excepto el primero)
            if indice > 1:
                time.sleep(delay_envio)
            
            # Log de progreso cada 10 emails
            if indice % 10 == 0:
                logger.info(f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)")

            # Verificar si el envío está habilitado
            if not _verificar_envio_habilitado(db, tipo_notificacion):
                logger.info(f"⏸️ Envío de {tipo_notificacion} está deshabilitado, saltando cliente {cliente_id}...")
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

            # Construir variables desde el resultado
            variables = variables_service.construir_variables_desde_dict(datos_query=resultado)

            # Reemplazar variables en plantilla
            asunto = variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables)
            cuerpo = variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables)

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

            # Obtener CCO configurados para este tipo
            cco_emails = _obtener_cco_configurados(db, tipo_notificacion)

            # Enviar email
            try:
                resultado_email = email_service.send_email(
                    to_emails=[str(correo_cliente)],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                    bcc_emails=cco_emails if cco_emails else None,
                )

                if resultado_email.get("success"):
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.utcnow()
                    nueva_notif.respuesta_servicio = resultado_email.get("message", "Email enviado exitosamente")
                    enviadas += 1
                    cco_info = f" (CCO: {', '.join(cco_emails)})" if cco_emails else ""
                    logger.info(f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, Prejudicial)")
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
            f"✅ [Scheduler] Prejudiciales completado: "
            f"{enviadas} enviadas, {fallidas} fallidas, {sin_plantilla} sin plantilla, {sin_email} sin email"
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en job de notificaciones prejudiciales: {e}", exc_info=True)
    finally:
        # Cerrar conexión SMTP reutilizada
        try:
            email_service.close_connection()
        except:
            pass
        db.close()


def iniciar_scheduler():
    """Inicia el scheduler con todas las tareas programadas"""
    try:
        # Agregar job para notificaciones previas (4 AM diariamente)
        scheduler.add_job(
            calcular_notificaciones_previas_job,
            trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
            id="notificaciones_previas",
            name="Calcular y Enviar Notificaciones Previas",
            replace_existing=True,
        )

        # Agregar job para día de pago (4 AM diariamente)
        scheduler.add_job(
            calcular_notificaciones_dia_pago_job,
            trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
            id="notificaciones_dia_pago",
            name="Calcular y Enviar Notificaciones Día de Pago",
            replace_existing=True,
        )

        # Agregar job para notificaciones retrasadas (4 AM diariamente)
        scheduler.add_job(
            calcular_notificaciones_retrasadas_job,
            trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
            id="notificaciones_retrasadas",
            name="Calcular y Enviar Notificaciones Retrasadas",
            replace_existing=True,
        )

        # Agregar job para notificaciones prejudiciales (4 AM diariamente)
        scheduler.add_job(
            calcular_notificaciones_prejudiciales_job,
            trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
            id="notificaciones_prejudiciales",
            name="Calcular y Enviar Notificaciones Prejudiciales",
            replace_existing=True,
        )

        # Iniciar scheduler
        scheduler.start()
        logger.info("✅ Scheduler iniciado correctamente")
        logger.info("📅 Jobs programados para ejecutarse diariamente a las 4:00 AM:")
        logger.info("   - Notificaciones Previas (5, 3, 1 días antes)")
        logger.info("   - Día de Pago (Día 0)")
        logger.info("   - Notificaciones Retrasadas (1, 3, 5 días atrasado)")
        logger.info("   - Notificaciones Prejudiciales (2+ cuotas atrasadas)")
        logger.info(
            "📧 Todos los jobs calcularán notificaciones y enviarán correos automáticamente usando plantillas y configuración de email"
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
