"""
Servicio para manejar mensajes entrantes de WhatsApp (Meta API).
Flujo cobranza: bienvenida → cédula (E, J o V + 6-11 dígitos) → foto papeleta (máx. 3 intentos) → guardar en Drive + OCR + digitalizar.
Las imágenes se guardan en pagos_whatsapp con link_imagen (Google Drive).
"""
import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.whatsapp import WhatsAppMessage, WhatsAppContact
from app.core.whatsapp_config_holder import get_whatsapp_config, sync_from_db as whatsapp_sync_from_db
from app.models.cliente import Cliente
from app.models.pagos_whatsapp import PagosWhatsapp
from app.models.conversacion_cobranza import ConversacionCobranza
from app.models.pagos_informe import PagosInforme
from app.models.mensaje_whatsapp import MensajeWhatsapp

logger = logging.getLogger(__name__)


def _telefono_normalizado(phone: str) -> str:
    """Teléfono solo dígitos para guardar/consultar historial."""
    return re.sub(r"\D", "", (phone or "").strip())


def guardar_mensaje_whatsapp(
    db: Session,
    telefono: str,
    direccion: str,
    body: str,
    message_type: str = "text",
) -> None:
    """Guarda un mensaje en el historial para mostrar copia de la conversación en Comunicaciones."""
    if not telefono or direccion not in ("INBOUND", "OUTBOUND"):
        return
    phone = _telefono_normalizado(telefono)
    if len(phone) < 8:
        return
    try:
        row = MensajeWhatsapp(
            telefono=phone,
            direccion=direccion,
            body=(body or "").strip() or None,
            message_type=message_type or "text",
            timestamp=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
    except Exception as e:
        logger.debug("No se pudo guardar mensaje en historial: %s", e)
        db.rollback()

# Mensajes del flujo (Configuración AI / WhatsApp puede personalizarlos después)
MENSAJE_BIENVENIDA = (
    "Hola, bienvenido al servicio de cobranza de Rapicredit. "
    "Primero ingresa tu número de cédula sin guiones intermedios "
    "(formato: debe empezar por una de las 3 letras E, J o V, seguido de entre 6 y 11 números; puede ser mayúsculas o minúsculas)."
)
MENSAJE_CONFIRMACION = "Confirma que el siguiente reporte de pago se realizará a cargo de {nombre}. ¿Sí o No?"
MENSAJE_CONFIRMACION_SIN_NOMBRE = "Confirma que el siguiente reporte de pago se realizará a cargo del titular de la cédula {cedula}. ¿Sí o No?"
MENSAJE_GRACIAS_PIDE_FOTO = (
    "Gracias{nombre_gracias}. Ahora adjunta una foto clara de tu papeleta de depósito o recibo de pago válido, a unos 20 cm. "
    "Si no es un recibo válido o no se ve bien se te pedirá otra; máximo 3 intentos. Al tercero se almacena."
)
MENSAJE_CEDULA_INVALIDA = (
    "La cédula debe empezar por una de las 3 letras E, J o V, seguido de entre 6 y 11 números, sin guiones ni signos. "
    "Ejemplos: E1234567, V12345678, J1234567 o EVJ1234567. Vuelve a ingresarla."
)
MENSAJE_VUELVE_CEDULA = "Por favor escribe de nuevo tu número de cédula (E, J o V seguido de 6 a 11 números)."
MENSAJE_RESPONDE_SI_NO = "Por favor responde Sí o No: ¿El reporte de pago es a cargo de {nombre}?"
# Si envían foto pero aún no han confirmado (Sí/No), no se pide cédula de nuevo; se recuerda el paso actual.
MENSAJE_PRIMERO_CONFIRMA_LUEGO_FOTO = (
    "Primero confirma con Sí o No que el reporte de pago es a tu nombre. Después envía la foto de tu papeleta de depósito."
)
MENSAJE_CONTINUAMOS_SIN_CONFIRMAR = "Continuamos. Envía una foto clara de tu papeleta de depósito (recibo de pago válido) a 20 cm."
MENSAJE_ENVIA_FOTO = "Por favor adjunta una foto clara de tu papeleta de depósito o recibo de pago válido, a 20 cm."
MENSAJE_FOTO_POCO_CLARA = (
    "Necesitamos un recibo de pago válido (papeleta de depósito). La imagen no es válida o no se ve bien. "
    "Toma otra foto a 20 cm de tu papeleta. Intento {n}/3. Al tercer intento se almacenará la que envíes. "
    "Si tienes dudas, llama al 0424-4359435."
)
MENSAJE_RECIBIDO = "Gracias. Tu reporte de pago (cédula {cedula}) quedó registrado. Si necesitas algo más, llama al 0424-4359435."
# Al aceptar por 3.er intento (imagen no clara): siempre se acepta y se indica que si no está clara los contactaremos.
MENSAJE_RECIBIDO_TERCER_INTENTO = (
    "Gracias. Hemos registrado tu reporte (cédula {cedula}). "
    "Si no tenemos clara la imagen, te contactaremos. Para otras consultas: 0424-4359435."
)
OBSERVACION_NO_CONFIRMA = "No confirma identidad"
# Cuando falla descarga/configuración/procesamiento de imagen: siempre responder para no dejar al usuario sin respuesta.
MENSAJE_IMAGEN_NO_PROCESADA = (
    "No pudimos procesar tu imagen en este momento. Por favor intenta enviar otra foto clara de tu papeleta a 20 cm, "
    "o llama al 0424-4359435 para que te atiendan."
)
# Cuando piden algo que no es reportar pago (información, hablar con alguien, etc.), se les indica que llamen.
MENSAJE_OTRA_INFORMACION = (
    "Para otras consultas te atendemos por teléfono. Llama al 0424-4359435 y un asistente te atenderá."
)

# Si la conversación lleva más de esta cantidad de minutos sin actividad, se trata como nuevo caso (pedir cédula e imagen de nuevo).
MINUTOS_INACTIVIDAD_NUEVO_CASO = 5


def _conversacion_obsoleta(conv: ConversacionCobranza, minutos: int = MINUTOS_INACTIVIDAD_NUEVO_CASO) -> bool:
    """True si la conversación no tiene actividad desde hace más de `minutos` minutos; así se trata como nuevo reporte (volver a cédula e imagen)."""
    if not conv or not getattr(conv, "updated_at", None):
        return True
    try:
        ultima = conv.updated_at
        if getattr(ultima, "tzinfo", None) is not None:
            ultima = ultima.replace(tzinfo=None)
        delta = datetime.utcnow() - ultima
        return delta > timedelta(minutes=minutos)
    except (TypeError, ValueError):
        return True


def _reiniciar_como_nuevo_caso(conv: ConversacionCobranza, db: Session) -> None:
    """Reinicia la conversación para tratarla como nuevo caso (nuevo reporte de pago)."""
    conv.estado = "esperando_cedula"
    conv.cedula = None
    conv.nombre_cliente = None
    conv.intento_foto = 0
    conv.intento_confirmacion = 0
    conv.observacion = None
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)
    logger.info("Conversación %s reiniciada como nuevo caso (inactividad > %s min).", conv.telefono, MINUTOS_INACTIVIDAD_NUEVO_CASO)


# Validación cédula: debe empezar por E, J o V (una de las 3 letras) + 6 a 11 dígitos. Acepta E1234567, V12345678, J1234567, EVJ1234567.
CEDULA_PATTERN_E = re.compile(r"^[Ee]\d{6,11}$")
CEDULA_PATTERN_J = re.compile(r"^[Jj]\d{6,11}$")
CEDULA_PATTERN_V = re.compile(r"^[Vv]\d{6,11}$")
CEDULA_PATTERN_EVJ = re.compile(r"^[Ee][Vv][Jj]\d{6,11}$")


def _normalize_cedula_input(text: str) -> str:
    """Quita espacios y guiones del texto para validar cédula."""
    return (text or "").strip().replace(" ", "").replace("-", "").replace("_", "")


def _validar_cedula_evj(text: str) -> bool:
    """True si el texto empieza por E, J o V seguido de 6 a 11 números (p. ej. E1234567, V12345678, EVJ1234567)."""
    s = _normalize_cedula_input(text)
    if not s:
        return False
    return bool(
        CEDULA_PATTERN_E.match(s)
        or CEDULA_PATTERN_J.match(s)
        or CEDULA_PATTERN_V.match(s)
        or CEDULA_PATTERN_EVJ.match(s)
    )


def _cedula_normalizada(text: str) -> str:
    """Devuelve la cédula con letras en mayúsculas (E, J, V o EVJ + números)."""
    s = _normalize_cedula_input(text)
    if not _validar_cedula_evj(s):
        return s
    return s.upper()


def _es_respuesta_si(text: str) -> bool:
    """True si el texto se interpreta como Sí (confirmación)."""
    t = (text or "").strip().lower()
    return t in ("sí", "si", "s", "yes", "y", "1", "confirmo", "correcto", "ok", "dale")


def _es_respuesta_no(text: str) -> bool:
    """True si el texto se interpreta como No."""
    t = (text or "").strip().lower()
    return t in ("no", "n", "negativo", "incorrecto")


# Palabras/frases que sugieren que piden otra cosa (no reportar pago): información, hablar con alguien, etc.
_PALABRAS_OTRA_INFORMACION = (
    "informacion", "información", "consulta", "consultar", "hablar", "llamar", "atención", "atencion",
    "ayuda", "horario", "direccion", "dirección", "contacto", "telefono", "teléfono", "otra cosa",
    "alguien", "asistente", "humano", "persona", "ejecutivo", "asesor", "soporte", "reclamo", "queja",
)


def _pide_otra_informacion(text: str) -> bool:
    """True si el mensaje parece pedir información o atención que no sea reportar un pago."""
    t = (text or "").strip().lower()
    if len(t) < 3:
        return False
    return any(p in t for p in _PALABRAS_OTRA_INFORMACION)


def _buscar_nombre_cliente_por_cedula(db: Session, cedula: str) -> Optional[str]:
    """Busca en tabla clientes por cédula y devuelve nombres (ej. Lucia Gavilanez)."""
    if not cedula or not cedula.strip():
        return None
    nombre = db.execute(select(Cliente.nombres).where(Cliente.cedula == cedula.strip()).limit(1)).scalar_one_or_none()
    return (nombre or "").strip() if nombre else None


def _periodo_envio_actual() -> str:
    """Devuelve '6am' | '1pm' | '4h30' según la hora actual (America/Caracas)."""
    try:
        import pytz
        tz = pytz.timezone("America/Caracas")
        now = datetime.now(tz).time()
        h, m = now.hour, now.minute
        if h < 6 or (h == 6 and m == 0):
            return "6am"
        if h < 13 or (h == 13 and m == 0):
            return "1pm"
        if h < 16 or (h == 16 and m < 30):
            return "4h30"
        return "6am"
    except Exception:
        return "6am"


async def _send_whatsapp_async(to_phone: str, body: str) -> bool:
    """Envía un mensaje de texto por WhatsApp (async)."""
    import httpx
    digits = re.sub(r"\D", "", (to_phone or "").strip())
    if not digits or len(digits) < 10:
        return False
    whatsapp_sync_from_db()
    cfg = get_whatsapp_config()
    token = (cfg.get("access_token") or "").strip()
    phone_number_id = (cfg.get("phone_number_id") or "").strip()
    api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
    if not token or not phone_number_id:
        return False
    body = (body or "").strip()[:4096]
    if not body:
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{api_url}/{phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": digits,
                    "type": "text",
                    "text": {"body": body},
                },
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        if r.is_success:
            logger.info("WhatsApp enviado a %s (cobranza)", digits[:6] + "***")
            return True
        logger.warning("WhatsApp API error %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.exception("Error enviando WhatsApp: %s", e)
        return False


class WhatsAppService:
    """Servicio para procesar mensajes de WhatsApp (flujo cobranza + guardar imágenes)."""

    def __init__(self):
        self.logger = logger

    async def process_incoming_message(
        self,
        message: WhatsAppMessage,
        contact: Optional[WhatsAppContact] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante. Texto: flujo cédula/foto. Imagen: intento de papeleta (máx. 3), luego Drive + OCR + digitalización.
        """
        try:
            self.logger.info("Procesando mensaje WhatsApp - ID: %s, From: %s, Type: %s", message.id, message.from_, message.type)
            message_data = {
                "message_id": message.id,
                "from_number": message.from_,
                "timestamp": message.timestamp,
                "message_type": message.type,
                "processed_at": datetime.utcnow().isoformat(),
            }
            if message.type == "text" and message.text and db:
                message_data["text_content"] = message.text.body
                guardar_mensaje_whatsapp(db, message.from_, "INBOUND", message.text.body, "text")
                result = await self._process_text_cobranza(message.text.body, message.from_, db)
                message_data.update(result)
                if result.get("response_text"):
                    await _send_whatsapp_async(message.from_, result["response_text"])
                    guardar_mensaje_whatsapp(db, message.from_, "OUTBOUND", result["response_text"], "text")
            elif message.type == "image" and message.image and db:
                body_imagen = (message.image.caption or "").strip() if message.image.caption else "[Imagen]"
                guardar_mensaje_whatsapp(db, message.from_, "INBOUND", body_imagen, "image")
                result = await self._process_image_message(message, db)
                message_data.update(result)
                if result.get("response_text"):
                    await _send_whatsapp_async(message.from_, result["response_text"])
                    guardar_mensaje_whatsapp(db, message.from_, "OUTBOUND", result["response_text"], "text")
            elif message.type == "document" and message.document and db:
                body_doc = (message.document.caption or "").strip() or (message.document.filename or "[Documento]")
                guardar_mensaje_whatsapp(db, message.from_, "INBOUND", body_doc, "image")
                mime = (message.document.mime_type or "").strip().lower()
                fname = (message.document.filename or "").strip().lower()
                es_imagen = mime.startswith("image/") or any(fname.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"))
                if es_imagen:
                    result = await self._process_image_message(message, db, media_id=message.document.id)
                    message_data.update(result)
                    if result.get("response_text"):
                        await _send_whatsapp_async(message.from_, result["response_text"])
                        guardar_mensaje_whatsapp(db, message.from_, "OUTBOUND", result["response_text"], "text")
                else:
                    msg = "Por favor envía una foto (imagen) de tu papeleta de depósito, no un documento (PDF u otro archivo)."
                    message_data["status"] = "document_no_imagen"
                    message_data["response_text"] = msg
                    await _send_whatsapp_async(message.from_, msg)
                    guardar_mensaje_whatsapp(db, message.from_, "OUTBOUND", msg, "text")
            else:
                message_data["status"] = "unsupported_type"
                message_data["note"] = f"Tipo {message.type} no soportado"
                msg = "Solo puedo procesar texto e imágenes. Para reportar tu pago envía una foto clara de tu papeleta de depósito."
                message_data["response_text"] = msg
                await _send_whatsapp_async(message.from_, msg)
                if db:
                    guardar_mensaje_whatsapp(db, message.from_, "OUTBOUND", msg, "text")
            if contact:
                message_data["contact_wa_id"] = contact.wa_id
                if contact.profile:
                    message_data["contact_name"] = contact.profile.get("name")
            return {"success": True, "message_id": message.id, "data": message_data}
        except Exception as e:
            self.logger.error("Error procesando mensaje WhatsApp: %s", str(e), exc_info=True)
            # Si fue imagen, enviar al menos un mensaje al usuario para no dejar el bot "desconectado"
            if (message.type == "image" or (message.type == "document" and message.document)) and message.from_:
                try:
                    await _send_whatsapp_async(message.from_, MENSAJE_IMAGEN_NO_PROCESADA)
                except Exception:
                    pass
            return {"success": False, "error": str(e), "message_id": getattr(message, "id", None)}

    async def _process_text_cobranza(self, text: str, from_number: str, db: Session) -> Dict[str, Any]:
        """Flujo: bienvenida → cédula (E, J o V + 6-11 dígitos) → confirmación (Sí/No, máx. 3 intentos) → pedir foto. Respuestas por nombre cuando hay cliente."""
        phone = "".join(c for c in from_number if c.isdigit())
        if len(phone) < 10:
            phone = from_number
        conv = db.execute(select(ConversacionCobranza).where(ConversacionCobranza.telefono == phone)).scalar_one_or_none()
        if not conv:
            conv = ConversacionCobranza(telefono=phone, estado="esperando_cedula", intento_foto=0, intento_confirmacion=0)
            db.add(conv)
            db.commit()
            db.refresh(conv)
            if _pide_otra_informacion(text):
                return {"status": "otra_informacion", "response_text": MENSAJE_OTRA_INFORMACION}
            return {"status": "welcome", "response_text": MENSAJE_BIENVENIDA}
        # Si lleva mucho tiempo sin actividad, tratar como nuevo caso (nuevo reporte de pago)
        if _conversacion_obsoleta(conv):
            _reiniciar_como_nuevo_caso(conv, db)
            if _pide_otra_informacion(text):
                return {"status": "otra_informacion", "response_text": MENSAJE_OTRA_INFORMACION}
            return {"status": "welcome", "response_text": MENSAJE_BIENVENIDA}
        if conv.estado == "esperando_cedula":
            if not _validar_cedula_evj(text):
                if _pide_otra_informacion(text):
                    return {"status": "otra_informacion", "response_text": MENSAJE_OTRA_INFORMACION}
                # Siempre mostrar bienvenida/instrucción cuando aún no han dado cédula válida (flujo debe pedir cédula claro)
                return {"status": "cedula_invalida", "response_text": MENSAJE_BIENVENIDA}
            cedula = _cedula_normalizada(text)
            nombre_cliente = _buscar_nombre_cliente_por_cedula(db, cedula)
            conv.cedula = cedula
            conv.nombre_cliente = nombre_cliente
            conv.estado = "esperando_confirmacion"
            conv.intento_confirmacion = 1
            conv.intento_foto = 0
            conv.observacion = None
            conv.updated_at = datetime.utcnow()
            db.commit()
            if nombre_cliente:
                msg = MENSAJE_CONFIRMACION.format(nombre=nombre_cliente)
            else:
                msg = MENSAJE_CONFIRMACION_SIN_NOMBRE.format(cedula=cedula)
            return {"status": "cedula_ok_confirmar", "response_text": msg}
        if conv.estado == "esperando_confirmacion":
            if _es_respuesta_si(text):
                conv.estado = "esperando_foto"
                conv.intento_foto = 0
                conv.intento_confirmacion = 0
                conv.updated_at = datetime.utcnow()
                db.commit()
                nombre_gracias = f", {conv.nombre_cliente}" if conv.nombre_cliente else ""
                msg = MENSAJE_GRACIAS_PIDE_FOTO.format(nombre_gracias=nombre_gracias)
                return {"status": "confirmado", "response_text": msg}
            if _es_respuesta_no(text):
                conv.estado = "esperando_cedula"
                conv.cedula = None
                conv.nombre_cliente = None
                conv.intento_confirmacion = 0
                conv.observacion = None
                conv.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "no_confirmado_vuelve_cedula", "response_text": MENSAJE_VUELVE_CEDULA}
            if _pide_otra_informacion(text):
                return {"status": "otra_informacion", "response_text": MENSAJE_OTRA_INFORMACION}
            intento = (conv.intento_confirmacion or 0) + 1
            conv.intento_confirmacion = intento
            conv.updated_at = datetime.utcnow()
            if intento >= 3:
                conv.observacion = OBSERVACION_NO_CONFIRMA
                conv.estado = "esperando_foto"
                conv.intento_foto = 0
                db.commit()
                return {"status": "sin_confirmar_sigue", "response_text": MENSAJE_CONTINUAMOS_SIN_CONFIRMAR}
            db.commit()
            nombre = conv.nombre_cliente or conv.cedula or "el titular"
            return {"status": "pide_si_no", "response_text": MENSAJE_RESPONDE_SI_NO.format(nombre=nombre)}
        if conv.estado == "esperando_foto":
            if _pide_otra_informacion(text):
                return {"status": "otra_informacion", "response_text": MENSAJE_OTRA_INFORMACION}
            nombre = conv.nombre_cliente or ""
            if nombre:
                return {"status": "remind_foto", "response_text": f"{nombre}, {MENSAJE_ENVIA_FOTO}"}
            return {"status": "remind_foto", "response_text": MENSAJE_ENVIA_FOTO}
        return {"status": "processed"}

    async def _process_image_message(self, message: WhatsAppMessage, db: Session, media_id: Optional[str] = None) -> Dict[str, Any]:
        """Descarga imagen (por message.image.id o media_id si es documento tipo imagen); si hay conversación en esperando_foto: intento 1/2 → pedir de nuevo, 3 → Drive + pagos_whatsapp + OCR + digitalizar."""
        media_id = media_id or (message.image and message.image.id)
        if not media_id:
            logger.info("Imagen no digitalizada: falta ID de media (no_digitaliza=image_no_id)")
            return {"status": "image_no_id", "note": "Falta ID de media", "response_text": MENSAJE_ENVIA_FOTO}
        phone = "".join(c for c in message.from_ if c.isdigit())
        if len(phone) < 10:
            phone = message.from_
        conv = db.execute(select(ConversacionCobranza).where(ConversacionCobranza.telefono == phone)).scalar_one_or_none()
        if not conv:
            logger.info("Imagen no digitalizada: no hay conversación para teléfono %s (no_digitaliza=need_cedula)", phone[:6] + "***")
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        # Si lleva mucho tiempo sin actividad, tratar como nuevo caso (pedir cédula de nuevo)
        if _conversacion_obsoleta(conv):
            _reiniciar_como_nuevo_caso(conv, db)
            logger.info("Imagen no digitalizada: conversación obsoleta, reiniciada (no_digitaliza=need_cedula)")
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        # Protocolo: no volver a pedir cédula si ya la dio. Si está en confirmación, pedir Sí/No primero; luego foto.
        if conv.estado == "esperando_cedula":
            logger.info("Imagen no digitalizada: estado=esperando_cedula (no_digitaliza=need_cedula)")
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        if conv.estado == "esperando_confirmacion":
            nombre = conv.nombre_cliente or conv.cedula or "el titular"
            logger.info("Imagen no digitalizada: estado=esperando_confirmacion, pedir Sí/No primero (no_digitaliza=primero_confirmar)")
            return {"status": "primero_confirmar", "response_text": MENSAJE_PRIMERO_CONFIRMA_LUEGO_FOTO}
        if conv.estado != "esperando_foto" or not conv.cedula:
            logger.info("Imagen no digitalizada: estado=%s o sin cédula (no_digitaliza=need_cedula)", conv.estado or "?")
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        whatsapp_sync_from_db()
        cfg = get_whatsapp_config()
        token = (cfg.get("access_token") or "").strip()
        api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
        if not token:
            logger.warning(
                "Imagen no digitalizada: Access token WhatsApp no configurado (no_digitaliza=image_skipped). "
                "Usuario ve 'No pudimos procesar tu imagen'; nada en Drive."
            )
            return {"status": "image_skipped", "note": "Token no configurado", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{api_url}/{media_id}", headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                data = r.json()
                media_url = data.get("url")
                if not media_url:
                    logger.warning(
                        "Imagen no digitalizada: Meta no devolvió URL del media (no_digitaliza=image_no_url). "
                        "Usuario ve 'No pudimos procesar'; nada en Drive."
                    )
                    return {"status": "image_no_url", "note": "Meta no devolvió URL", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
                r2 = await client.get(media_url, headers={"Authorization": f"Bearer {token}"})
                r2.raise_for_status()
                image_bytes = r2.content
        except Exception as e:
            logger.exception(
                "Imagen no digitalizada: error descargando imagen (no_digitaliza=image_error). "
                "Usuario ve 'No pudimos procesar'; nada en Drive. Error: %s", e
            )
            db.rollback()
            return {"status": "image_error", "note": f"descarga: {e!s}", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        if not image_bytes:
            logger.warning(
                "Imagen no digitalizada: imagen vacía (no_digitaliza=image_empty). "
                "Usuario ve 'No pudimos procesar'; nada en Drive."
            )
            return {"status": "image_empty", "note": "Imagen vacía", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        conv.intento_foto = (conv.intento_foto or 0) + 1
        # OCR sobre toda imagen (sin depender del análisis): probar que está activo/configurado y tener datos si aceptamos
        ocr_data_early = {"fecha_deposito": "NA", "nombre_banco": "NA", "numero_deposito": "NA", "numero_documento": "NA", "cantidad": "NA", "humano": ""}
        try:
            from app.services.ocr_service import extract_from_image
            ocr_data_early = extract_from_image(image_bytes)
            logger.info(
                "OCR ejecutado (toda imagen): banco=%s, fecha=%s, cantidad=%s, humano=%s",
                ocr_data_early.get("nombre_banco") or "NA",
                ocr_data_early.get("fecha_deposito") or "NA",
                ocr_data_early.get("cantidad") or "NA",
                ocr_data_early.get("humano") or "",
            )
        except Exception as e:
            logger.warning("OCR no aplicado (verificar Vision/config): %s", e)
        # Evaluación por IA: texto OCR + prompt corto → aceptable + mensaje conversacional (gracias o pedir otra foto)
        ocr_text = ""
        try:
            from app.services.ocr_service import get_full_text
            ocr_text = get_full_text(image_bytes) or ""
        except Exception as e:
            logger.debug("OCR texto para IA: %s", e)
        try:
            from app.services.ai_imagen_respuesta import evaluar_imagen_y_respuesta
            aceptable, mensaje_ia = evaluar_imagen_y_respuesta(ocr_text, conv.cedula or "", db)
        except Exception as e:
            logger.warning("IA imagen falló, usando fallback por claridad: %s", e)
            from app.services.ocr_service import imagen_suficientemente_clara
            aceptable = imagen_suficientemente_clara(image_bytes)
            mensaje_ia = MENSAJE_RECIBIDO.format(cedula=conv.cedula or "N/A") if aceptable else MENSAJE_FOTO_POCO_CLARA.format(n=conv.intento_foto)
        # Aceptar a la primera: procesar siempre (Drive + OCR + BD + Sheet) para comprobar si el fallo es flujo o OCR/conexión.
        aceptar = aceptable or conv.intento_foto >= 1
        aceptado_por_tercer_intento = aceptar and not aceptable and conv.intento_foto >= 3  # True solo si aceptamos por ser 3.er intento (no por IA)
        if not aceptar:
            logger.info(
                "Imagen no digitalizada: IA no aceptó, intento %d/3 (no_digitaliza=photo_retry); respuesta: %s",
                conv.intento_foto, mensaje_ia[:80],
            )
            conv.updated_at = datetime.utcnow()
            db.commit()
            return {
                "status": "photo_retry",
                "intento_foto": conv.intento_foto,
                "response_text": mensaje_ia,
            }
        # Imagen aceptada (IA) o tercer intento: guardar en Drive, pagos_whatsapp, OCR, pagos_informes, Sheet. Si algo falla, igual responder al usuario.
        logger.info("Digitalizando imagen: cedula=%s intento=%d aceptable=%s", conv.cedula, conv.intento_foto, aceptable)
        try:
            link_imagen = None
            try:
                from app.services.google_drive_service import upload_image_and_get_link
                link_imagen = upload_image_and_get_link(image_bytes, filename=f"papeleta_{phone}_{datetime.utcnow().strftime('%Y%m%d%H%M')}.jpg")
            except Exception as e:
                logger.exception("Error subiendo a Drive: %s", e)
            if not link_imagen:
                logger.warning("Drive: subida fallida o no configurada; link_imagen=NA. Revisa OAuth conectado, ID carpeta y que la carpeta esté compartida con la cuenta OAuth.")
                link_imagen = "NA"
            row_pw = PagosWhatsapp(
                fecha=datetime.utcnow(),
                cedula_cliente=conv.cedula,
                imagen=image_bytes,
                link_imagen=link_imagen,
            )
            db.add(row_pw)
            db.commit()
            db.refresh(row_pw)
            logger.info("Imagen guardada pagos_whatsapp id=%s cedula=%s link=%s", row_pw.id, conv.cedula, link_imagen[:50] if link_imagen else "N/A")
            # Usar datos OCR ya obtenidos para toda imagen (no volver a llamar Vision)
            periodo = _periodo_envio_actual()
            fecha_dep = ocr_data_early.get("fecha_deposito") or "NA"
            nombre_banco = ocr_data_early.get("nombre_banco") or "NA"
            numero_dep = ocr_data_early.get("numero_deposito") or "NA"
            numero_doc = ocr_data_early.get("numero_documento") or "NA"
            cantidad = ocr_data_early.get("cantidad") or "NA"
            humano_col = (ocr_data_early.get("humano") or "").strip() or None
            observacion_informe = conv.observacion or None
            informe = PagosInforme(
                cedula=conv.cedula,
                fecha_deposito=fecha_dep,
                nombre_banco=nombre_banco,
                numero_deposito=numero_dep,
                numero_documento=numero_doc,
                cantidad=cantidad,
                humano=humano_col,
                link_imagen=link_imagen,
                observacion=observacion_informe,
                pagos_whatsapp_id=row_pw.id,
                periodo_envio=periodo,
                fecha_informe=datetime.utcnow(),
            )
            db.add(informe)
            db.commit()
            db.refresh(informe)
            logger.info(
                "Imagen digitalizada: pagos_whatsapp_id=%s pagos_informe_id=%s cedula=%s fecha_dep=%s banco=%s",
                row_pw.id, informe.id, conv.cedula, fecha_dep, nombre_banco,
            )
            try:
                from app.services.google_sheets_informe_service import append_row
                logger.info("Escribiendo fila en Sheet: cedula=%s link_imagen=%s", conv.cedula, "OK" if link_imagen and link_imagen != "NA" else "NA")
                sheet_ok = append_row(conv.cedula, fecha_dep, nombre_banco, numero_dep, numero_doc, cantidad, link_imagen, periodo, observacion=observacion_informe, humano=humano_col or "")
                if not sheet_ok:
                    logger.warning("Sheets: no se escribió la fila (digitalización en BD OK). Revisa Configuración > Informe pagos: credenciales, ID hoja, y que la hoja esté compartida con la cuenta.")
            except Exception as e:
                logger.exception("Error escribiendo en Sheet (digitalización en BD OK): %s", e)
            cedula_guardada = conv.cedula
            conv.intento_foto = 0
            conv.estado = "esperando_cedula"
            conv.cedula = None
            conv.nombre_cliente = None
            conv.observacion = None
            conv.updated_at = datetime.utcnow()
            db.commit()
            # Respuesta al usuario: si la imagen fue aceptada por IA/claridad → mensaje_ia; si aceptamos por 3.er intento → indicar que si no está clara los contactaremos
            if aceptable:
                response_text = mensaje_ia
            elif aceptado_por_tercer_intento:
                response_text = MENSAJE_RECIBIDO_TERCER_INTENTO.format(cedula=cedula_guardada or "N/A")
            else:
                response_text = MENSAJE_RECIBIDO.format(cedula=cedula_guardada or "N/A")
            return {"status": "image_saved", "pagos_whatsapp_id": row_pw.id, "cedula_cliente": cedula_guardada, "response_text": response_text}
        except Exception as e:
            logger.exception(
                "Digitalización fallida (Drive/OCR/BD/Sheet). Usuario ve 'No pudimos procesar'; puede no haber nada en Drive. Error: %s",
                e,
            )
            try:
                db.rollback()
            except Exception:
                pass
            if conv.intento_foto >= 3:
                response_cierre = MENSAJE_RECIBIDO_TERCER_INTENTO.format(cedula=conv.cedula or "N/A")
            else:
                response_cierre = MENSAJE_IMAGEN_NO_PROCESADA
            return {"status": "image_error", "note": str(e), "response_text": response_cierre}
