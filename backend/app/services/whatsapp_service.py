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

# Prefijo único para buscar en logs (Render): "INFORME_PAGOS" = flujo imagen; "INFORME_PAGOS FALLO" = solo errores.
LOG_TAG_INFORME = "[INFORME_PAGOS]"
LOG_TAG_FALLO = "[INFORME_PAGOS] FALLO"


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
# Confirmación de recepción (IA solo para respuestas bot; OCR extrae y decide). Tras OCR se envían datos al chat.
MENSAJE_RECIBIMOS_COMPROBANTE = (
    "Recibimos tu comprobante (papeleta/recibo de pago). "
    "Estos son los datos que leímos. Responde *SÍ* para confirmar o escribe las correcciones "
    "(ej: Fecha 01/02/2025, Cantidad 100.50)."
)
MENSAJE_DATOS_CONFIRMADOS = "Gracias. Datos confirmados y registrados. Si necesitas algo más, llama al 0424-4359435."
MENSAJE_DATOS_ACTUALIZADOS = "Gracias. Hemos actualizado los datos con tus correcciones. Quedó registrado."
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
    conv.pagos_informe_id_pendiente = None
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


# Solo estos campos se confirman/editan con el cliente: cédula, cantidad, número de documento.
CAMPOS_CONFIRMACION = ("cedula", "cantidad", "numero_documento")


def _parsear_edicion_confirmacion(text: str) -> Dict[str, Any]:
    """
    Parsea correcciones del cliente solo para: cédula, cantidad, número de documento.
    Usado en esperando_confirmacion_datos. No modifica otras columnas.
    """
    out: Dict[str, Any] = {}
    if not text or len(text.strip()) < 2:
        return out
    t = text.strip()
    # Cantidad: número con opcional . o , decimal
    m = re.search(r"(?:cantidad|total|monto)\s*[:\-]?\s*([\d\s.,]+)", t, re.I)
    if m:
        val = re.sub(r"\s", "", m.group(1).replace(",", "."))
        if re.match(r"^\d+\.?\d*$", val):
            out["cantidad"] = val
    # Número documento
    m = re.search(r"(?:n(?:umero|º|úmero)?\s*(?:documento|doc|recibo)\s*[:\-]?)\s*([^\n,]+?)(?=\s*(?:,|$))", t, re.I)
    if m:
        out["numero_documento"] = m.group(1).strip()[:100]
    # Cédula: E/J/V + dígitos
    m = re.search(r"(?:cedula|cédula|cedula)\s*[:\-]?\s*([EeVvJj]\d{6,11})", t, re.I)
    if m:
        out["cedula"] = m.group(1).strip().upper()[:20]
    return out


def _parsear_edicion_datos_informe(text: str) -> Dict[str, Any]:
    """
    Parsea mensaje del usuario con correcciones (todos los campos).
    En el flujo de confirmación usamos _parsear_edicion_confirmacion (solo cedula, cantidad, numero_documento).
    """
    return _parsear_edicion_confirmacion(text)


def _mensaje_confirmacion_datos_ocr(cedula: str, cantidad: str, numero_documento: str, db: Session) -> str:
    """
    Mensaje para confirmar únicamente cédula, cantidad y número de documento.
    Se escribe primero en Google Sheet; luego se pide al cliente que confirme. IA genera la conversación.
    """
    try:
        from app.services.ai_imagen_respuesta import generar_mensaje_confirmacion_datos
        return generar_mensaje_confirmacion_datos(cedula, cantidad, numero_documento, db)
    except Exception as e:
        logger.debug("IA confirmación datos: %s", e)
    return (
        "Recibimos tu comprobante. Datos leídos:\n\n"
        f"• Cédula: {cedula or '—'}\n• Cantidad: {cantidad or '—'}\n• Nº documento: {numero_documento or '—'}\n\n"
        "Responde *SÍ* para confirmar o escribe las correcciones (ej: Cantidad 100.50, Nº documento 12345)."
    )


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
            self.logger.error(
                "%s %s | excepción no capturada: %s",
                LOG_TAG_FALLO, "mensaje_whatsapp", str(e),
                exc_info=True,
            )
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
        # Tras OCR: cliente confirma datos o escribe correcciones; actualizamos columnas si edita
        if conv.estado == "esperando_confirmacion_datos":
            informe_id = getattr(conv, "pagos_informe_id_pendiente", None)
            phone_mask = (phone[:6] + "***") if len(phone) >= 6 else "***"
            logger.info("%s Confirmación datos: estado=esperando_confirmacion_datos informe_id=%s telefono=%s", LOG_TAG_INFORME, informe_id, phone_mask)
            if not informe_id or not db:
                logger.warning("%s Confirmación datos: sin informe_id o db, reiniciando flujo", LOG_TAG_FALLO)
                conv.estado = "esperando_cedula"
                conv.pagos_informe_id_pendiente = None
                conv.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "processed", "response_text": MENSAJE_BIENVENIDA}
            informe = db.get(PagosInforme, informe_id)
            if not informe:
                logger.warning("%s Confirmación datos: informe_id=%s no encontrado en BD", LOG_TAG_FALLO, informe_id)
                conv.estado = "esperando_cedula"
                conv.pagos_informe_id_pendiente = None
                conv.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "processed", "response_text": "No encontramos el registro. " + MENSAJE_BIENVENIDA}
            if _es_respuesta_si(text):
                logger.info("%s Confirmación datos: cliente confirmó SÍ | informe_id=%s telefono=%s", LOG_TAG_INFORME, informe_id, phone_mask)
                informe.estado_conciliacion = "CONCILIADO"
                conv.pagos_informe_id_pendiente = None
                conv.intento_foto = 0
                conv.estado = "esperando_cedula"
                cedula_guardada = conv.cedula
                conv.cedula = None
                conv.nombre_cliente = None
                conv.observacion = None
                conv.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(informe)
                try:
                    from app.services.google_sheets_informe_service import update_row_for_informe
                    update_row_for_informe(informe)
                except Exception as e:
                    logger.warning("%s No se pudo actualizar Sheet con estado CONCILIADO: %s", LOG_TAG_INFORME, e)
                return {"status": "datos_confirmados", "response_text": MENSAJE_DATOS_CONFIRMADOS}
            edits = _parsear_edicion_confirmacion((text or "").strip())
            # Solo actualizar cédula, cantidad y numero_documento; no generar otra fila, solo editar la misma
            edits = {k: v for k, v in edits.items() if k in CAMPOS_CONFIRMACION and v is not None}
            if edits:
                logger.info("%s Confirmación datos: cliente editó campos | informe_id=%s campos=%s", LOG_TAG_INFORME, informe_id, list(edits.keys()))
                informe.estado_conciliacion = "REVISAR"
                for k, v in edits.items():
                    if hasattr(informe, k):
                        if k == "cedula" and isinstance(v, str):
                            setattr(informe, k, v[:20])
                        elif k == "cantidad" and isinstance(v, str):
                            setattr(informe, k, v[:50])
                        elif k == "numero_documento" and isinstance(v, str):
                            setattr(informe, k, v[:100])
                db.commit()
                db.refresh(informe)
                try:
                    from app.services.google_sheets_informe_service import update_row_for_informe
                    update_row_for_informe(informe)
                except Exception as e:
                    logger.warning("%s No se pudo actualizar Sheet con correcciones: %s", LOG_TAG_INFORME, e)
                conv.pagos_informe_id_pendiente = None
                conv.intento_foto = 0
                conv.estado = "esperando_cedula"
                conv.cedula = None
                conv.nombre_cliente = None
                conv.observacion = None
                conv.updated_at = datetime.utcnow()
                db.commit()
                return {"status": "datos_actualizados", "response_text": MENSAJE_DATOS_ACTUALIZADOS}
            logger.info("%s Confirmación datos: respuesta no SÍ ni edición parseable | informe_id=%s telefono=%s", LOG_TAG_INFORME, informe_id, phone_mask)
            return {"status": "pide_confirmar_o_editar", "response_text": "Responde *SÍ* para confirmar o escribe las correcciones (ej: Cantidad 100.50, Nº documento 12345)."}
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
        phone = "".join(c for c in message.from_ if c.isdigit())
        if len(phone) < 10:
            phone = message.from_
        phone_mask = (phone[:6] + "***") if len(phone) >= 6 else "***"
        if not media_id:
            logger.warning("%s %s | status=image_no_id note=Falta ID de media telefono=%s", LOG_TAG_FALLO, "no_digitaliza", phone_mask)
            return {"status": "image_no_id", "note": "Falta ID de media", "response_text": MENSAJE_ENVIA_FOTO}
        conv = db.execute(select(ConversacionCobranza).where(ConversacionCobranza.telefono == phone)).scalar_one_or_none()
        if not conv:
            logger.info("%s Inicio imagen sin conversación | telefono=%s (no_digitaliza=need_cedula)", LOG_TAG_INFORME, phone_mask)
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        if _conversacion_obsoleta(conv):
            _reiniciar_como_nuevo_caso(conv, db)
            logger.info("%s Conversación obsoleta reiniciada | telefono=%s (no_digitaliza=need_cedula)", LOG_TAG_INFORME, phone_mask)
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        if conv.estado == "esperando_cedula":
            logger.info("%s Imagen rechazada estado=esperando_cedula | telefono=%s (no_digitaliza=need_cedula)", LOG_TAG_INFORME, phone_mask)
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        if conv.estado == "esperando_confirmacion":
            logger.info("%s Imagen rechazada estado=esperando_confirmacion | telefono=%s (no_digitaliza=primero_confirmar)", LOG_TAG_INFORME, phone_mask)
            return {"status": "primero_confirmar", "response_text": MENSAJE_PRIMERO_CONFIRMA_LUEGO_FOTO}
        if conv.estado == "esperando_confirmacion_datos":
            logger.info("%s Imagen ignorada estado=esperando_confirmacion_datos | telefono=%s", LOG_TAG_INFORME, phone_mask)
            return {"status": "confirma_o_edita_texto", "response_text": "Responde *SÍ* para confirmar (cédula, cantidad y Nº documento) o escribe las correcciones por texto (ej: Cantidad 100.50, Nº documento 12345)."}
        if conv.estado != "esperando_foto" or not conv.cedula:
            logger.info("%s Imagen rechazada estado=%s sin cedula | telefono=%s (no_digitaliza=need_cedula)", LOG_TAG_INFORME, conv.estado or "?", phone_mask)
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        logger.info(
            "%s FLUJO_OCR INICIO | pasos: 1=descarga 2=OCR 3=Drive 4=BD 5=Sheet 6=confirmacion | telefono=%s media_id=%s cedula=%s",
            LOG_TAG_INFORME, phone_mask, media_id, conv.cedula,
        )
        logger.info("%s Inicio procesamiento imagen | telefono=%s media_id=%s cedula=%s intento_foto=%s", LOG_TAG_INFORME, phone_mask, media_id, conv.cedula, conv.intento_foto or 0)
        whatsapp_sync_from_db()
        cfg = get_whatsapp_config()
        token = (cfg.get("access_token") or "").strip()
        api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
        if not token:
            logger.warning("%s %s | status=image_skipped note=Token WhatsApp no configurado telefono=%s", LOG_TAG_FALLO, "no_digitaliza", phone_mask)
            return {"status": "image_skipped", "note": "Token no configurado", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{api_url}/{media_id}", headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                data = r.json()
                media_url = data.get("url")
                if not media_url:
                    logger.warning("%s %s | status=image_no_url note=Meta no devolvió URL telefono=%s", LOG_TAG_FALLO, "no_digitaliza", phone_mask)
                    return {"status": "image_no_url", "note": "Meta no devolvió URL", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
                r2 = await client.get(media_url, headers={"Authorization": f"Bearer {token}"})
                r2.raise_for_status()
                image_bytes = r2.content
        except Exception as e:
            logger.exception("%s %s | status=image_error note=descarga fallida telefono=%s error=%s", LOG_TAG_FALLO, "no_digitaliza", phone_mask, e)
            db.rollback()
            return {"status": "image_error", "note": f"descarga: {e!s}", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        if not image_bytes:
            logger.warning("%s %s | status=image_empty note=Imagen vacía telefono=%s", LOG_TAG_FALLO, "no_digitaliza", phone_mask)
            return {"status": "image_empty", "note": "Imagen vacía", "response_text": MENSAJE_IMAGEN_NO_PROCESADA}
        logger.info("%s Imagen descargada | telefono=%s bytes=%d", LOG_TAG_INFORME, phone_mask, len(image_bytes) or 0)
        conv.intento_foto = (conv.intento_foto or 0) + 1
        # OCR sobre toda imagen (sin depender del análisis): probar que está activo/configurado y tener datos si aceptamos
        ocr_data_early = {"fecha_deposito": "NA", "nombre_banco": "NA", "numero_deposito": "NA", "numero_documento": "NA", "cantidad": "NA", "humano": ""}
        logger.info("%s [OCR] INICIO extract_from_image | telefono=%s image_bytes=%d", LOG_TAG_INFORME, phone_mask, len(image_bytes or b""))
        try:
            from app.services.ocr_service import extract_from_image
            ocr_data_early = extract_from_image(image_bytes)
            logger.info(
                "%s [OCR] RESULTADO extract_from_image | telefono=%s banco=%s fecha=%s numero_dep=%s numero_doc=%s cantidad=%s humano=%s",
                LOG_TAG_INFORME, phone_mask,
                ocr_data_early.get("nombre_banco") or "NA",
                ocr_data_early.get("fecha_deposito") or "NA",
                ocr_data_early.get("numero_deposito") or "NA",
                ocr_data_early.get("numero_documento") or "NA",
                ocr_data_early.get("cantidad") or "NA",
                ocr_data_early.get("humano") or "",
            )
        except Exception as e:
            logger.exception(
                "%s [OCR] FALLO extract_from_image (Vision/config) | telefono=%s error=%s",
                LOG_TAG_FALLO, phone_mask, e,
            )
        # Decisión "aceptable" solo por OCR: si extrajo al menos un dato útil o marcó HUMANO (revisión humana), es aceptable.
        # La IA no decide; solo se usa opcionalmente para el mensaje cuando hay bastante texto.
        def _aceptable_por_ocr(data: dict) -> bool:
            if not data:
                return False
            na_vals = (None, "NA", "")
            campos_utiles = ("nombre_banco", "fecha_deposito", "cantidad", "numero_deposito", "numero_documento")
            alguno = any((data.get(k) or "").strip() not in na_vals for k in campos_utiles)
            humano = (data.get("humano") or "").strip() == "HUMANO"
            return bool(alguno or humano)
        aceptable = _aceptable_por_ocr(ocr_data_early)
        logger.info("%s [OCR] Decisión por OCR: aceptable=%s (datos extraídos o HUMANO)", LOG_TAG_INFORME, aceptable)
        # IA no evalúa documento; solo se usa para respuestas del bot en otros contextos. Mensaje según aceptable.
        mensaje_ia = MENSAJE_RECIBIDO.format(cedula=conv.cedula or "N/A") if aceptable else MENSAJE_FOTO_POCO_CLARA.format(n=conv.intento_foto)
        # OCR decide: si no extrajo nada, pedir otra foto (photo_retry); en el 3.º intento aceptar siempre.
        aceptar = aceptable or conv.intento_foto >= 3
        aceptado_por_tercer_intento = aceptar and not aceptable and conv.intento_foto >= 3
        if not aceptar:
            logger.info(
                "%s Imagen no aceptada por IA intento %d/3 (no_digitaliza=photo_retry) | telefono=%s",
                LOG_TAG_INFORME, conv.intento_foto, phone_mask,
            )
            conv.updated_at = datetime.utcnow()
            db.commit()
            return {
                "status": "photo_retry",
                "intento_foto": conv.intento_foto,
                "response_text": mensaje_ia,
            }
        logger.info("%s Digitalizando (Drive+BD+Sheet) | telefono=%s cedula=%s intento=%d aceptable=%s", LOG_TAG_INFORME, phone_mask, conv.cedula, conv.intento_foto, aceptable)
        try:
            link_imagen = None
            try:
                from app.services.google_drive_service import upload_image_and_get_link
                link_imagen = upload_image_and_get_link(image_bytes, filename=f"papeleta_{phone}_{datetime.utcnow().strftime('%Y%m%d%H%M')}.jpg")
            except Exception as e:
                logger.exception("%s %s | Drive upload exception | telefono=%s error=%s", LOG_TAG_FALLO, "digitalizacion", phone_mask, e)
            if not link_imagen:
                logger.warning("%s Drive subida fallida o no configurada link_imagen=NA | telefono=%s", LOG_TAG_INFORME, phone_mask)
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
            logger.info("%s pagos_whatsapp guardado | id=%s telefono=%s cedula=%s link=%s", LOG_TAG_INFORME, row_pw.id, phone_mask, conv.cedula, (link_imagen[:50] + "..." if link_imagen and len(link_imagen) > 50 else link_imagen or "NA"))
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
                nombre_cliente=(conv.nombre_cliente or "").strip() or None,
                estado_conciliacion=None,
                telefono=phone,
            )
            db.add(informe)
            db.commit()
            db.refresh(informe)
            logger.info(
                "Informe guardado en BD id=%s | cedula=%s cantidad=%s",
                informe.id, conv.cedula, cantidad,
            )
            logger.info(
                "%s OK digitalización completa | pagos_whatsapp_id=%s pagos_informe_id=%s telefono=%s cedula=%s banco=%s",
                LOG_TAG_INFORME, row_pw.id, informe.id, phone_mask, conv.cedula, nombre_banco,
            )
            try:
                from app.services.google_sheets_informe_service import append_row
                logger.info("%s Escribiendo Sheet | telefono=%s cedula=%s", LOG_TAG_INFORME, phone_mask, conv.cedula)
                sheet_ok = append_row(
                    conv.cedula, fecha_dep, nombre_banco, numero_dep, numero_doc, cantidad, link_imagen, periodo,
                    observacion=observacion_informe,
                    nombre_cliente=(conv.nombre_cliente or "").strip() or "",
                    estado_conciliacion="",
                    timestamp_registro=informe.fecha_informe,
                    telefono=phone or "",
                )
                if not sheet_ok:
                    logger.warning("%s Sheets no escribió fila (BD OK) | telefono=%s cedula=%s", LOG_TAG_INFORME, phone_mask, conv.cedula)
            except Exception as e:
                logger.exception("%s %s | Sheet append_row exception | telefono=%s error=%s", LOG_TAG_FALLO, "digitalizacion", phone_mask, e)
            # Enviar al chat los datos extraídos por OCR para que el cliente confirme o edite (IA no evalúa documento)
            conv.estado = "esperando_confirmacion_datos"
            conv.pagos_informe_id_pendiente = informe.id
            conv.updated_at = datetime.utcnow()
            db.commit()
            logger.info("%s FLUJO_OCR OK hasta Sheet | estado=esperando_confirmacion_datos informe_id=%s telefono=%s", LOG_TAG_INFORME, informe.id, phone_mask)
            response_text = _mensaje_confirmacion_datos_ocr(conv.cedula, cantidad, numero_doc, db)
            return {"status": "image_saved_confirmar_datos", "pagos_whatsapp_id": row_pw.id, "pagos_informe_id": informe.id, "response_text": response_text}
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception(
                "%s %s | digitalización fallida (Drive/OCR/BD/Sheet) telefono=%s cedula=%s error=%s",
                LOG_TAG_FALLO, "digitalizacion", phone_mask, getattr(conv, "cedula", "?"), e,
            )
            logger.error(
                "%s CAUSA mensaje 'No pudimos procesar': tipo=%s mensaje=%s",
                LOG_TAG_FALLO, type(e).__name__, str(e),
            )
            if conv.intento_foto >= 3:
                response_cierre = MENSAJE_RECIBIDO_TERCER_INTENTO.format(cedula=conv.cedula or "N/A")
            else:
                response_cierre = MENSAJE_IMAGEN_NO_PROCESADA
            return {"status": "image_error", "note": str(e), "response_text": response_cierre}
