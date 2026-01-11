"""
Scheduler para tareas automáticas
Usa APScheduler para ejecutar tareas programadas
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import SessionLocal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler(daemon=True)

# Variable para evitar inicialización múltiple
_scheduler_inicializado = False


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
                logger.warning(
                    f"⚠️ Valor inválido para delay_envio_email_segundos: {config.valor}, usando 2 segundos por defecto"
                )
        return 2.0  # 2 segundos por defecto
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo delay de envío: {e}, usando 2 segundos por defecto")
        return 2.0


async def _enviar_whatsapp_desde_scheduler(
    db: "Session",
    cliente_id: int,
    tipo_notificacion: str,
    asunto: str,
    cuerpo: str,
    telefono_cliente: str,
) -> bool:
    """
    Función auxiliar para enviar WhatsApp desde el scheduler

    Args:
        db: Sesión de base de datos
        cliente_id: ID del cliente
        tipo_notificacion: Tipo de notificación
        asunto: Asunto del mensaje
        cuerpo: Cuerpo del mensaje
        telefono_cliente: Teléfono del cliente

    Returns:
        True si se envió exitosamente, False si hubo error
    """
    try:
        from app.models.notificacion import Notificacion
        from app.services.whatsapp_service import WhatsAppService

        # Verificar que el cliente tenga teléfono
        if not telefono_cliente or not telefono_cliente.strip():
            return False

        # Crear registro de notificación WhatsApp
        notif_whatsapp = Notificacion(
            cliente_id=cliente_id,
            tipo=tipo_notificacion,
            canal="WHATSAPP",
            asunto=asunto,
            mensaje=cuerpo,
            estado="PENDIENTE",
        )
        db.add(notif_whatsapp)
        db.commit()
        db.refresh(notif_whatsapp)

        # Enviar WhatsApp
        whatsapp_service = WhatsAppService(db=db)

        # ✅ INTEGRACIÓN CON TEMPLATES DE META
        # Intentar usar template si está configurado
        from app.services.whatsapp_template_mapper import WhatsAppTemplateMapper

        template_name = WhatsAppTemplateMapper.get_template_name(tipo_notificacion)
        template_parameters = None

        if template_name:
            # Extraer variables del mensaje para los parámetros del template
            # Obtener variables desde la BD si es posible
            try:
                from app.models.amortizacion import Cuota
                from app.models.cliente import Cliente
                from app.models.prestamo import Prestamo
                from app.services.variables_notificacion_service import VariablesNotificacionService

                cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
                if cliente:
                    # Intentar obtener préstamo y cuota si están disponibles
                    prestamo = None
                    cuota = None

                    # Buscar préstamo activo del cliente
                    if cliente.prestamos:
                        prestamo = next((p for p in cliente.prestamos if p.estado == "ACTIVO"), None)
                        if prestamo and prestamo.cuotas:
                            # Buscar cuota más próxima a vencer
                            cuota = next((c for c in prestamo.cuotas if c.estado == "PENDIENTE"), None)

                    # Construir variables
                    variables_service = VariablesNotificacionService(db=db)
                    variables = variables_service.construir_variables_desde_bd(
                        cliente=cliente,
                        prestamo=prestamo,
                        cuota=cuota,
                    )

                    # Extraer parámetros del template
                    template_parameters = WhatsAppTemplateMapper.extract_template_parameters(
                        message=cuerpo, variables=variables, template_name=template_name
                    )

                    logger.info(
                        f"📋 [TEMPLATE] Usando template '{template_name}' con {len(template_parameters)} parámetros "
                        f"para notificación {tipo_notificacion}"
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ [TEMPLATE] Error extrayendo variables para template '{template_name}': {e}. "
                    f"Usando mensaje completo como parámetro único."
                )

        # Enviar mensaje (con template si está configurado, sin template si no)
        resultado_whatsapp = await whatsapp_service.send_message(
            to_number=str(telefono_cliente),
            message=cuerpo,
            template_name=template_name,
            template_parameters=template_parameters,
        )

        if resultado_whatsapp.get("success"):
            notif_whatsapp.estado = "ENVIADA"
            notif_whatsapp.enviada_en = datetime.utcnow()
            notif_whatsapp.respuesta_servicio = resultado_whatsapp.get("message", "WhatsApp enviado exitosamente")
            db.commit()
            logger.info(f"✅ WhatsApp enviado a {telefono_cliente} (Cliente {cliente_id}, {tipo_notificacion})")
            return True
        else:
            notif_whatsapp.estado = "FALLIDA"
            notif_whatsapp.error_mensaje = resultado_whatsapp.get("message", "Error desconocido")
            notif_whatsapp.intentos = 1
            db.commit()
            logger.warning(
                f"⚠️ Error enviando WhatsApp a {telefono_cliente} (Cliente {cliente_id}): {resultado_whatsapp.get('message')}"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Excepción enviando WhatsApp a {telefono_cliente} (Cliente {cliente_id}): {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return False


def calcular_notificaciones_previas_job():
    """Job que calcula y ENVÍA notificaciones previas a las 4 AM"""
    db = SessionLocal()
    try:
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
                logger.info(
                    f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)"
                )
            cliente_id = resultado["cliente_id"]
            dias_antes = resultado["dias_antes_vencimiento"]
            correo_cliente = resultado.get("correo", "")

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
                    logger.info(
                        f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, {dias_antes} días antes)"
                    )

                    # ✅ Enviar también por WhatsApp si el cliente tiene teléfono
                    telefono_cliente = resultado.get("telefono", "")
                    if telefono_cliente and telefono_cliente.strip():
                        try:
                            # Intentar usar asyncio.run, si falla porque hay un loop corriendo, usar run_until_complete
                            try:
                                asyncio.run(
                                    _enviar_whatsapp_desde_scheduler(
                                        db=db,
                                        cliente_id=cliente_id,
                                        tipo_notificacion=tipo_notificacion,
                                        asunto=asunto,
                                        cuerpo=cuerpo,
                                        telefono_cliente=telefono_cliente,
                                    )
                                )
                            except RuntimeError:
                                # Si ya hay un event loop corriendo, crear uno nuevo
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(
                                        _enviar_whatsapp_desde_scheduler(
                                            db=db,
                                            cliente_id=cliente_id,
                                            tipo_notificacion=tipo_notificacion,
                                            asunto=asunto,
                                            cuerpo=cuerpo,
                                            telefono_cliente=telefono_cliente,
                                        )
                                    )
                                finally:
                                    loop.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Error enviando WhatsApp (no crítico): {e}")
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
        except Exception:
            pass
        db.close()


def calcular_notificaciones_dia_pago_job():
    """Job que calcula y ENVÍA notificaciones del día de pago a las 4 AM"""
    db = SessionLocal()
    try:
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
                logger.info(
                    f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)"
                )

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

                    # ✅ Enviar también por WhatsApp si el cliente tiene teléfono
                    telefono_cliente = resultado.get("telefono", "")
                    if telefono_cliente and telefono_cliente.strip():
                        try:
                            # Intentar usar asyncio.run, si falla porque hay un loop corriendo, usar run_until_complete
                            try:
                                asyncio.run(
                                    _enviar_whatsapp_desde_scheduler(
                                        db=db,
                                        cliente_id=cliente_id,
                                        tipo_notificacion=tipo_notificacion,
                                        asunto=asunto,
                                        cuerpo=cuerpo,
                                        telefono_cliente=telefono_cliente,
                                    )
                                )
                            except RuntimeError:
                                # Si ya hay un event loop corriendo, crear uno nuevo
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(
                                        _enviar_whatsapp_desde_scheduler(
                                            db=db,
                                            cliente_id=cliente_id,
                                            tipo_notificacion=tipo_notificacion,
                                            asunto=asunto,
                                            cuerpo=cuerpo,
                                            telefono_cliente=telefono_cliente,
                                        )
                                    )
                                finally:
                                    loop.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Error enviando WhatsApp (no crítico): {e}")
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
        except Exception:
            pass
        db.close()


def calcular_notificaciones_retrasadas_job():
    """Job que calcula y ENVÍA notificaciones retrasadas a las 4 AM"""
    db = SessionLocal()
    try:
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
                logger.info(
                    f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)"
                )

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
                    logger.info(
                        f"✅ Email enviado a {correo_cliente}{cco_info} (Cliente {cliente_id}, {dias_atrasado} días atrasado)"
                    )

                    # ✅ Enviar también por WhatsApp si el cliente tiene teléfono
                    telefono_cliente = resultado.get("telefono", "")
                    if telefono_cliente and telefono_cliente.strip():
                        try:
                            # Intentar usar asyncio.run, si falla porque hay un loop corriendo, usar run_until_complete
                            try:
                                asyncio.run(
                                    _enviar_whatsapp_desde_scheduler(
                                        db=db,
                                        cliente_id=cliente_id,
                                        tipo_notificacion=tipo_notificacion,
                                        asunto=asunto,
                                        cuerpo=cuerpo,
                                        telefono_cliente=telefono_cliente,
                                    )
                                )
                            except RuntimeError:
                                # Si ya hay un event loop corriendo, crear uno nuevo
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(
                                        _enviar_whatsapp_desde_scheduler(
                                            db=db,
                                            cliente_id=cliente_id,
                                            tipo_notificacion=tipo_notificacion,
                                            asunto=asunto,
                                            cuerpo=cuerpo,
                                            telefono_cliente=telefono_cliente,
                                        )
                                    )
                                finally:
                                    loop.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Error enviando WhatsApp (no crítico): {e}")
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
        except Exception:
            pass
        db.close()


def calcular_notificaciones_prejudiciales_job():
    """Job que calcula y ENVÍA notificaciones prejudiciales a las 4 AM"""
    db = SessionLocal()
    try:
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
        # sin_plantilla no se usa en esta función (se verifica al inicio y retorna si no existe)
        sin_email = 0

        # Inicializar servicio de variables
        variables_service = VariablesNotificacionService(db=db)

        # Obtener delay configurado entre envíos
        delay_envio = _obtener_delay_envio(db)
        logger.info(f"⏱️ Delay configurado entre envíos: {delay_envio} segundos")

        # Procesar cada notificación (solo una por cliente para evitar duplicados)
        clientes_procesados = set()
        tipo_notificacion = "PREJUDICIAL"

        # ✅ Verificar plantilla UNA VEZ al inicio (más eficiente)
        plantilla = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.tipo == tipo_notificacion, NotificacionPlantilla.activa.is_(True))
            .first()
        )

        if not plantilla:
            logger.warning(
                f"⚠️ No hay plantilla activa para tipo {tipo_notificacion}. "
                f"Se encontraron {len(resultados)} clientes elegibles, pero no se enviarán notificaciones. "
                f"Por favor, crea y activa una plantilla para {tipo_notificacion} en la configuración de notificaciones."
            )
            db.close()
            return

        # ✅ Verificar si el envío está habilitado UNA VEZ al inicio
        if not _verificar_envio_habilitado(db, tipo_notificacion):
            logger.info(
                f"⏸️ Envío de {tipo_notificacion} está deshabilitado. "
                f"Se encontraron {len(resultados)} clientes elegibles, pero no se enviarán notificaciones."
            )
            db.close()
            return

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
                logger.info(
                    f"📊 Progreso: {indice}/{total_resultados} emails procesados ({enviadas} enviadas, {fallidas} fallidas)"
                )

            # Verificar que el cliente tenga email
            if not correo_cliente:
                # ✅ Solo contar, no loguear cada uno (reducir verbosidad)
                sin_email += 1
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

                    # ✅ Enviar también por WhatsApp si el cliente tiene teléfono
                    telefono_cliente = resultado.get("telefono", "")
                    if telefono_cliente and telefono_cliente.strip():
                        try:
                            # Intentar usar asyncio.run, si falla porque hay un loop corriendo, usar run_until_complete
                            try:
                                asyncio.run(
                                    _enviar_whatsapp_desde_scheduler(
                                        db=db,
                                        cliente_id=cliente_id,
                                        tipo_notificacion=tipo_notificacion,
                                        asunto=asunto,
                                        cuerpo=cuerpo,
                                        telefono_cliente=telefono_cliente,
                                    )
                                )
                            except RuntimeError:
                                # Si ya hay un event loop corriendo, crear uno nuevo
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(
                                        _enviar_whatsapp_desde_scheduler(
                                            db=db,
                                            cliente_id=cliente_id,
                                            tipo_notificacion=tipo_notificacion,
                                            asunto=asunto,
                                            cuerpo=cuerpo,
                                            telefono_cliente=telefono_cliente,
                                        )
                                    )
                                finally:
                                    loop.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Error enviando WhatsApp (no crítico): {e}")
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
            f"✅ [Scheduler] Prejudiciales completado: " f"{enviadas} enviadas, {fallidas} fallidas, {sin_email} sin email"
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en job de notificaciones prejudiciales: {e}", exc_info=True)
    finally:
        # Cerrar conexión SMTP reutilizada
        try:
            email_service.close_connection()
        except Exception:
            pass
        db.close()


def _registrar_auditoria_reentrenamiento(
    db: "Session",
    nuevo_modelo: Optional[Any] = None,
    nuevas_metricas: Optional[dict] = None,
    modelo_activo: Optional[Any] = None,
    es_mejor: Optional[bool] = None,
    nuevo_accuracy: Optional[float] = None,
    nuevo_f1: Optional[float] = None,
    accuracy_actual: Optional[float] = None,
    f1_actual: Optional[float] = None,
):
    """Registra el reentrenamiento en auditoría"""
    try:
        from app.models.auditoria import Auditoria
        from app.models.user import User

        # Buscar usuario admin o sistema para registrar auditoría
        usuario_sistema = db.query(User).filter(User.is_admin == True).first()
        if not usuario_sistema:
            # Si no hay admin, buscar cualquier usuario
            usuario_sistema = db.query(User).first()

        if not usuario_sistema:
            logger.warning("⚠️ [Scheduler] No se encontró usuario para registrar auditoría")
            return

        # Determinar si se activó un nuevo modelo
        modelo_activado = None
        if modelo_activo:
            if es_mejor and nuevo_modelo:
                modelo_activado = nuevo_modelo
        elif nuevo_modelo:
            modelo_activado = nuevo_modelo

        detalles_auditoria = "Reentrenamiento automático del modelo ML Impago. "
        if modelo_activado:
            detalles_auditoria += f"Modelo activado: {modelo_activado.nombre} (ID: {modelo_activado.id}). "
            if nuevas_metricas:
                detalles_auditoria += f"Métricas: Accuracy={nuevas_metricas.get('accuracy', 0.0):.4f}, F1={nuevas_metricas.get('f1_score', 0.0):.4f}"
        else:
            detalles_auditoria += "Modelo no activado (métricas inferiores al actual). "
            if all(v is not None for v in [nuevo_accuracy, nuevo_f1, accuracy_actual, f1_actual]):
                detalles_auditoria += f"Nuevo modelo: Accuracy={nuevo_accuracy:.4f}, F1={nuevo_f1:.4f} vs Actual: Accuracy={accuracy_actual:.4f}, F1={f1_actual:.4f}"

        auditoria = Auditoria(
            usuario_id=usuario_sistema.id,
            accion="REENTRENAR_MODELO_ML",
            entidad="ML_IMPAGO",
            entidad_id=modelo_activado.id if modelo_activado else None,
            detalles=detalles_auditoria,
            ip_address="SISTEMA",
            user_agent="APScheduler",
            exito=True,
        )
        db.add(auditoria)
        db.commit()
        logger.info("📝 [Scheduler] Auditoría registrada: Reentrenamiento ML Impago")
    except Exception as audit_error:
        logger.warning(f"⚠️ [Scheduler] No se pudo registrar auditoría: {audit_error}")


def reentrenar_modelo_ml_impago_job():
    """
    Job que reentrena automáticamente el modelo ML de impago semanalmente.
    Compara métricas con el modelo actual y lo activa si es mejor.
    """
    db = SessionLocal()
    # Inicializar variables para auditoría
    nuevo_modelo = None
    nuevas_metricas = None
    modelo_activo = None
    es_mejor = None
    nuevo_accuracy = None
    nuevo_f1 = None
    accuracy_actual = None
    f1_actual = None

    try:
        from datetime import date, datetime

        from sqlalchemy.exc import OperationalError, ProgrammingError

        from app.api.v1.endpoints.ai_training import (
            _obtener_prestamos_aprobados_impago,
            _procesar_prestamos_para_entrenamiento,
        )
        from app.models.modelo_impago_cuotas import ModeloImpagoCuotas
        from app.models.prestamo import Prestamo
        from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

        logger.info("=" * 80)
        logger.info("🤖 [Scheduler] ===== INICIO REENTRENAMIENTO AUTOMÁTICO ML IMPAGO =====")
        logger.info(f"   Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # Validar que el servicio ML esté disponible
        if not ML_IMPAGO_SERVICE_AVAILABLE or MLImpagoCuotasService is None:
            logger.warning(
                "⚠️ [Scheduler] ML_IMPAGO_SERVICE_AVAILABLE es False o MLImpagoCuotasService no disponible, omitiendo reentrenamiento"
            )
            return

        # Validar que la tabla exista
        try:
            db.query(ModeloImpagoCuotas).limit(1).all()
        except (ProgrammingError, OperationalError) as db_error:
            error_msg = str(db_error).lower()
            if any(term in error_msg for term in ["does not exist", "no such table", "relation", "table"]):
                logger.warning("⚠️ [Scheduler] La tabla 'modelos_impago_cuotas' no existe. Omitiendo reentrenamiento.")
                return
            raise

        # Obtener préstamos aprobados
        logger.info("🔍 [Scheduler] Buscando préstamos aprobados para reentrenamiento...")
        prestamos = _obtener_prestamos_aprobados_impago(db)
        logger.info(f"📊 [Scheduler] Encontrados {len(prestamos)} préstamos aprobados")

        if len(prestamos) < 10:
            logger.warning(
                f"⚠️ [Scheduler] Solo hay {len(prestamos)} préstamos aprobados. "
                f"Se necesitan al menos 10 para entrenar. Omitiendo reentrenamiento."
            )
            return

        # Procesar préstamos para generar datos de entrenamiento
        ml_service = MLImpagoCuotasService()
        fecha_actual = date.today()
        logger.info(f"📅 [Scheduler] Fecha actual para cálculo de features: {fecha_actual}")

        training_data = _procesar_prestamos_para_entrenamiento(prestamos, ml_service, fecha_actual, db)

        if len(training_data) < 10:
            logger.warning(
                f"⚠️ [Scheduler] Solo se generaron {len(training_data)} muestras válidas. "
                f"Se necesitan al menos 10. Omitiendo reentrenamiento."
            )
            return

        logger.info(f"📊 [Scheduler] Iniciando entrenamiento con {len(training_data)} muestras...")

        # Entrenar modelo (usar Random Forest por defecto para reentrenamiento automático)
        try:
            resultado = ml_service.train_impago_model(
                training_data,
                algoritmo="random_forest",  # Algoritmo por defecto para reentrenamiento automático
                test_size=0.2,
                random_state=42,
            )
        except Exception as train_error:
            logger.error(f"❌ [Scheduler] Error durante entrenamiento: {train_error}", exc_info=True)
            return

        if not resultado.get("success"):
            error_msg = resultado.get("error", "Error desconocido")
            logger.error(f"❌ [Scheduler] Entrenamiento falló: {error_msg}")
            return

        # Obtener métricas del nuevo modelo
        nuevas_metricas = resultado["metrics"]
        nuevo_accuracy = nuevas_metricas.get("accuracy", 0.0)
        nuevo_f1 = nuevas_metricas.get("f1_score", 0.0)

        logger.info("📈 [Scheduler] Nuevo modelo entrenado:")
        logger.info(f"   - Accuracy: {nuevo_accuracy:.4f} ({nuevo_accuracy*100:.2f}%)")
        logger.info(f"   - F1 Score: {nuevo_f1:.4f} ({nuevo_f1*100:.2f}%)")
        logger.info(f"   - Precision: {nuevas_metricas.get('precision', 0.0):.4f}")
        logger.info(f"   - Recall: {nuevas_metricas.get('recall', 0.0):.4f}")

        # Obtener modelo actual activo
        modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()

        if modelo_activo:
            accuracy_actual = modelo_activo.accuracy or 0.0
            f1_actual = modelo_activo.f1_score or 0.0

            logger.info("📊 [Scheduler] Modelo actual activo:")
            logger.info(f"   - Nombre: {modelo_activo.nombre}")
            logger.info(f"   - Accuracy: {accuracy_actual:.4f} ({accuracy_actual*100:.2f}%)")
            logger.info(f"   - F1 Score: {f1_actual:.4f} ({f1_actual*100:.2f}%)")

            # Comparar métricas: activar nuevo modelo si es mejor o igual
            # Consideramos mejor si accuracy es mayor O si accuracy es igual pero f1 es mayor
            es_mejor = (nuevo_accuracy > accuracy_actual) or (nuevo_accuracy == accuracy_actual and nuevo_f1 >= f1_actual)

            if es_mejor:
                logger.info("✅ [Scheduler] Nuevo modelo es mejor o igual. Activando...")

                # Desactivar modelo actual
                modelo_activo.activo = False
                db.commit()

                # Crear y activar nuevo modelo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nuevo_modelo = ModeloImpagoCuotas(
                    nombre=f"Modelo Impago Cuotas {timestamp} (Auto)",
                    version="1.0.0",
                    algoritmo="random_forest",
                    accuracy=nuevas_metricas["accuracy"],
                    precision=nuevas_metricas["precision"],
                    recall=nuevas_metricas["recall"],
                    f1_score=nuevas_metricas["f1_score"],
                    roc_auc=nuevas_metricas.get("roc_auc"),
                    ruta_archivo=resultado["model_path"],
                    total_datos_entrenamiento=resultado["training_samples"],
                    total_datos_test=resultado["test_samples"],
                    test_size=0.2,
                    random_state=42,
                    activo=True,
                    usuario_id=None,  # Reentrenamiento automático, sin usuario específico
                    descripcion=f"Modelo reentrenado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} con {len(training_data)} muestras",
                    features_usadas=",".join(resultado.get("features", [])),
                )

                db.add(nuevo_modelo)
                db.commit()
                db.refresh(nuevo_modelo)

                logger.info(f"✅ [Scheduler] Nuevo modelo activado: {nuevo_modelo.nombre} (ID: {nuevo_modelo.id})")
                logger.info(
                    f"📊 [Scheduler] Mejora: Accuracy {accuracy_actual*100:.2f}% → {nuevo_accuracy*100:.2f}% "
                    f"(+{(nuevo_accuracy-accuracy_actual)*100:.2f}%)"
                )
            else:
                logger.info("⚠️ [Scheduler] Nuevo modelo no es mejor. Manteniendo modelo actual.")
                logger.info(
                    f"   Diferencia: Accuracy {nuevo_accuracy*100:.2f}% vs {accuracy_actual*100:.2f}% "
                    f"({(nuevo_accuracy-accuracy_actual)*100:.2f}%)"
                )

                # Guardar nuevo modelo como inactivo para referencia histórica
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nuevo_modelo = ModeloImpagoCuotas(
                    nombre=f"Modelo Impago Cuotas {timestamp} (Auto - No activado)",
                    version="1.0.0",
                    algoritmo="random_forest",
                    accuracy=nuevas_metricas["accuracy"],
                    precision=nuevas_metricas["precision"],
                    recall=nuevas_metricas["recall"],
                    f1_score=nuevas_metricas["f1_score"],
                    roc_auc=nuevas_metricas.get("roc_auc"),
                    ruta_archivo=resultado["model_path"],
                    total_datos_entrenamiento=resultado["training_samples"],
                    total_datos_test=resultado["test_samples"],
                    test_size=0.2,
                    random_state=42,
                    activo=False,
                    usuario_id=None,
                    descripcion=f"Modelo reentrenado automáticamente pero no activado (métricas inferiores al actual) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    features_usadas=",".join(resultado.get("features", [])),
                )

                db.add(nuevo_modelo)
                db.commit()

        else:
            # No hay modelo activo, activar el nuevo directamente
            logger.info("⚠️ [Scheduler] No hay modelo activo. Activando nuevo modelo...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_modelo = ModeloImpagoCuotas(
                nombre=f"Modelo Impago Cuotas {timestamp} (Auto)",
                version="1.0.0",
                algoritmo="random_forest",
                accuracy=nuevas_metricas["accuracy"],
                precision=nuevas_metricas["precision"],
                recall=nuevas_metricas["recall"],
                f1_score=nuevas_metricas["f1_score"],
                roc_auc=nuevas_metricas.get("roc_auc"),
                ruta_archivo=resultado["model_path"],
                total_datos_entrenamiento=resultado["training_samples"],
                total_datos_test=resultado["test_samples"],
                test_size=0.2,
                random_state=42,
                activo=True,
                usuario_id=None,
                descripcion=f"Primer modelo activado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} con {len(training_data)} muestras",
                features_usadas=",".join(resultado.get("features", [])),
            )

            db.add(nuevo_modelo)
            db.commit()
            db.refresh(nuevo_modelo)

            logger.info(f"✅ [Scheduler] Modelo activado: {nuevo_modelo.nombre} (ID: {nuevo_modelo.id})")

        logger.info("=" * 80)
        logger.info("✅ [Scheduler] ===== REENTRENAMIENTO AUTOMÁTICO COMPLETADO =====")
        logger.info("=" * 80)

        # Registrar en auditoría (las variables están en el scope del try)
        _registrar_auditoria_reentrenamiento(
            db, nuevo_modelo, nuevas_metricas, modelo_activo, es_mejor, nuevo_accuracy, nuevo_f1, accuracy_actual, f1_actual
        )

    except Exception as e:
        logger.error(f"❌ [Scheduler] Error en reentrenamiento automático ML Impago: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass

        # Registrar error en auditoría
        try:
            from app.models.auditoria import Auditoria
            from app.models.user import User

            usuario_sistema = db.query(User).filter(User.is_admin == True).first()
            if not usuario_sistema:
                usuario_sistema = db.query(User).first()

            if usuario_sistema:
                auditoria = Auditoria(
                    usuario_id=usuario_sistema.id,
                    accion="REENTRENAR_MODELO_ML",
                    entidad="ML_IMPAGO",
                    entidad_id=None,
                    detalles=f"Error en reentrenamiento automático: {str(e)}",
                    ip_address="SISTEMA",
                    user_agent="APScheduler",
                    exito=False,
                    mensaje_error=str(e),
                )
                db.add(auditoria)
                db.commit()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass


def iniciar_scheduler():
    """Inicia el scheduler con todas las tareas programadas"""
    global _scheduler_inicializado

    try:
        # ✅ PROTECCIÓN: Evitar inicialización múltiple usando variable global
        if _scheduler_inicializado:
            logger.debug("⚠️ Scheduler ya fue inicializado, omitiendo")
            return

        # ✅ PROTECCIÓN: Verificar si el scheduler ya está corriendo
        if scheduler.running:
            logger.warning("⚠️ Scheduler ya está corriendo, omitiendo inicialización")
            _scheduler_inicializado = True
            return

        # ✅ PROTECCIÓN: Verificar si los jobs ya existen antes de agregarlos
        try:
            existing_jobs = {job.id for job in scheduler.get_jobs()}
        except Exception:
            # Si no se pueden obtener jobs (scheduler no iniciado), asumir que no hay jobs
            existing_jobs = set()

        # Agregar job para notificaciones previas (4 AM diariamente)
        if "notificaciones_previas" not in existing_jobs:
            scheduler.add_job(
                calcular_notificaciones_previas_job,
                trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
                id="notificaciones_previas",
                name="Calcular y Enviar Notificaciones Previas",
                replace_existing=True,
            )
        else:
            logger.debug("Job 'notificaciones_previas' ya existe, omitiendo")

        # Agregar job para día de pago (4 AM diariamente)
        if "notificaciones_dia_pago" not in existing_jobs:
            scheduler.add_job(
                calcular_notificaciones_dia_pago_job,
                trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
                id="notificaciones_dia_pago",
                name="Calcular y Enviar Notificaciones Día de Pago",
                replace_existing=True,
            )
        else:
            logger.debug("Job 'notificaciones_dia_pago' ya existe, omitiendo")

        # Agregar job para notificaciones retrasadas (4 AM diariamente)
        if "notificaciones_retrasadas" not in existing_jobs:
            scheduler.add_job(
                calcular_notificaciones_retrasadas_job,
                trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
                id="notificaciones_retrasadas",
                name="Calcular y Enviar Notificaciones Retrasadas",
                replace_existing=True,
            )
        else:
            logger.debug("Job 'notificaciones_retrasadas' ya existe, omitiendo")

        # Agregar job para notificaciones prejudiciales (4 AM diariamente)
        if "notificaciones_prejudiciales" not in existing_jobs:
            scheduler.add_job(
                calcular_notificaciones_prejudiciales_job,
                trigger=CronTrigger(hour=4, minute=0),  # 4:00 AM todos los días
                id="notificaciones_prejudiciales",
                name="Calcular y Enviar Notificaciones Prejudiciales",
                replace_existing=True,
            )
        else:
            logger.debug("Job 'notificaciones_prejudiciales' ya existe, omitiendo")

        # Agregar job para reentrenamiento automático de ML Impago (domingos a las 3 AM)
        # Solo agregar si el servicio ML está disponible y las funciones auxiliares existen
        try:
            from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE

            # Verificar que las funciones auxiliares se puedan importar
            try:
                from app.api.v1.endpoints.ai_training import (
                    _obtener_prestamos_aprobados_impago,
                    _procesar_prestamos_para_entrenamiento,
                )

                funciones_disponibles = True
            except ImportError as import_error:
                logger.warning(
                    f"⚠️ No se pudieron importar funciones auxiliares de ML: {import_error}. Omitiendo job de reentrenamiento ML"
                )
                funciones_disponibles = False

            if ML_IMPAGO_SERVICE_AVAILABLE and funciones_disponibles:
                if "reentrenar_ml_impago" not in existing_jobs:
                    scheduler.add_job(
                        reentrenar_modelo_ml_impago_job,
                        trigger=CronTrigger(day_of_week=6, hour=3, minute=0),  # Domingo (6) a las 3:00 AM
                        id="reentrenar_ml_impago",
                        name="Reentrenamiento Automático ML Impago",
                        replace_existing=True,
                    )
                    logger.info("✅ Job de reentrenamiento ML Impago agregado correctamente")
                else:
                    logger.debug("Job 'reentrenar_ml_impago' ya existe, omitiendo")
            else:
                if not ML_IMPAGO_SERVICE_AVAILABLE:
                    logger.info("⚠️ ML_IMPAGO_SERVICE_AVAILABLE es False, omitiendo job de reentrenamiento ML")
                elif not funciones_disponibles:
                    logger.info("⚠️ Funciones auxiliares de ML no disponibles, omitiendo job de reentrenamiento ML")
        except ImportError as e:
            logger.warning(f"⚠️ No se pudo importar ML_IMPAGO_SERVICE_AVAILABLE: {e}. Omitiendo job de reentrenamiento ML")
        except Exception as e:
            logger.warning(f"⚠️ Error configurando job de reentrenamiento ML: {e}. Continuando sin este job", exc_info=True)

        # Iniciar scheduler solo si no está corriendo
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Scheduler iniciado correctamente")

            # Solo loggear jobs programados una vez cuando se inicia el scheduler
            logger.info("📅 Jobs programados:")
            logger.info("   Diariamente a las 4:00 AM:")
            logger.info("   - Notificaciones Previas (5, 3, 1 días antes)")
            logger.info("   - Día de Pago (Día 0)")
            logger.info("   - Notificaciones Retrasadas (1, 3, 5 días atrasado)")
            logger.info("   - Notificaciones Prejudiciales (2+ cuotas atrasadas)")
            logger.info("   Semanalmente (Domingos a las 3:00 AM):")
            logger.info("   - Reentrenamiento Automático ML Impago")
            logger.info(
                "📧 Todos los jobs calcularán notificaciones y enviarán correos automáticamente usando plantillas y configuración de email"
            )
        else:
            logger.debug("✅ Scheduler ya estaba corriendo, omitiendo logs de jobs")

        # Marcar como inicializado
        _scheduler_inicializado = True

    except Exception as e:
        logger.error(f"❌ Error iniciando scheduler: {e}", exc_info=True)


def detener_scheduler():
    """Detiene el scheduler"""
    global _scheduler_inicializado

    try:
        # ✅ PROTECCIÓN: Evitar detención múltiple
        if not _scheduler_inicializado:
            logger.debug("⚠️ Scheduler no estaba inicializado, omitiendo detención")
            return

        if scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler detenido correctamente")
            _scheduler_inicializado = False
        else:
            logger.debug("⚠️ Scheduler ya estaba detenido")
            _scheduler_inicializado = False
    except Exception as e:
        logger.error(f"❌ Error deteniendo scheduler: {e}", exc_info=True)
        _scheduler_inicializado = False
