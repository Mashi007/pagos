"""
Servicio para manejar mensajes entrantes de WhatsApp (Meta API).
Flujo cobranza: bienvenida → cédula (E, J o V + 6-11 dígitos) → foto papeleta (máx. 3 intentos) → guardar en Drive + OCR + digitalizar.
Las imágenes se guardan en pagos_whatsapp con link_imagen (Google Drive).
"""
import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime
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
    "Gracias{nombre_gracias}. Ahora toma una foto clara de tu papeleta de depósito a máxima altura de tu celular (cámara) a unos 20 cm de tu papeleta. "
    "Si no está clara se te pedirá que vuelvas a tomar la foto; máximo 3 intentos. Al tercero se almacena."
)
MENSAJE_CEDULA_INVALIDA = (
    "La cédula debe empezar por una de las 3 letras E, J o V, seguido de entre 6 y 11 números, sin guiones ni signos. "
    "Ejemplos: E1234567, V12345678, J1234567 o EVJ1234567. Vuelve a ingresarla."
)
MENSAJE_VUELVE_CEDULA = "Por favor escribe de nuevo tu número de cédula (E, J o V seguido de 6 a 11 números)."
MENSAJE_RESPONDE_SI_NO = "Por favor responde Sí o No: ¿El reporte de pago es a cargo de {nombre}?"
MENSAJE_CONTINUAMOS_SIN_CONFIRMAR = "Continuamos. Envía una foto clara de tu papeleta de depósito a 20 cm."
MENSAJE_ENVIA_FOTO = "Por favor envía una foto clara de tu papeleta de depósito a 20 cm."
MENSAJE_FOTO_POCO_CLARA = "La imagen no está lo suficientemente clara. Toma otra foto a 20 cm de tu papeleta. Intento {n}/3."
MENSAJE_RECIBIDO = "Gracias. (Cédula {cedula} reportada.)"
OBSERVACION_NO_CONFIRMA = "No confirma identidad"

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
            else:
                message_data["status"] = "unsupported_type"
                message_data["note"] = f"Tipo {message.type} no soportado"
            if contact:
                message_data["contact_wa_id"] = contact.wa_id
                if contact.profile:
                    message_data["contact_name"] = contact.profile.get("name")
            return {"success": True, "message_id": message.id, "data": message_data}
        except Exception as e:
            self.logger.error("Error procesando mensaje WhatsApp: %s", str(e), exc_info=True)
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
            return {"status": "welcome", "response_text": MENSAJE_BIENVENIDA}
        if conv.estado == "esperando_cedula":
            if not _validar_cedula_evj(text):
                return {"status": "cedula_invalida", "response_text": MENSAJE_CEDULA_INVALIDA}
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
            nombre = conv.nombre_cliente or ""
            if nombre:
                return {"status": "remind_foto", "response_text": f"{nombre}, {MENSAJE_ENVIA_FOTO}"}
            return {"status": "remind_foto", "response_text": MENSAJE_ENVIA_FOTO}
        return {"status": "processed"}

    async def _process_image_message(self, message: WhatsAppMessage, db: Session) -> Dict[str, Any]:
        """Descarga imagen; si hay conversación en esperando_foto: intento 1/2 → pedir de nuevo, 3 → Drive + pagos_whatsapp + OCR + digitalizar."""
        phone = "".join(c for c in message.from_ if c.isdigit())
        if len(phone) < 10:
            phone = message.from_
        conv = db.execute(select(ConversacionCobranza).where(ConversacionCobranza.telefono == phone)).scalar_one_or_none()
        if not conv or conv.estado != "esperando_foto" or not conv.cedula:
            return {"status": "need_cedula", "response_text": MENSAJE_BIENVENIDA}
        whatsapp_sync_from_db()
        cfg = get_whatsapp_config()
        token = (cfg.get("access_token") or "").strip()
        api_url = (cfg.get("api_url") or "https://graph.facebook.com/v18.0").rstrip("/")
        if not token:
            logger.warning("Access token WhatsApp no configurado.")
            return {"status": "image_skipped", "note": "Token no configurado"}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{api_url}/{message.image.id}", headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                data = r.json()
                media_url = data.get("url")
                if not media_url:
                    return {"status": "image_no_url", "note": "Meta no devolvió URL"}
                r2 = await client.get(media_url, headers={"Authorization": f"Bearer {token}"})
                r2.raise_for_status()
                image_bytes = r2.content
        except Exception as e:
            logger.exception("Error descargando imagen: %s", e)
            db.rollback()
            return {"status": "image_error", "note": str(e)}
        if not image_bytes:
            return {"status": "image_empty", "note": "Imagen vacía"}
        conv.intento_foto = (conv.intento_foto or 0) + 1
        # Verificación real de claridad: Google Vision OCR; si detecta suficiente texto, se acepta en el primer intento
        clara = False
        try:
            from app.services.ocr_service import imagen_suficientemente_clara
            clara = imagen_suficientemente_clara(image_bytes)
        except Exception as e:
            logger.debug("Claridad imagen no comprobada: %s", e)
        aceptar = clara or conv.intento_foto >= 3
        if not aceptar:
            logger.info("Foto papeleta rechazada por claridad (intento %d/3); se pide otra foto.", conv.intento_foto)
            conv.updated_at = datetime.utcnow()
            db.commit()
            return {
                "status": "photo_retry",
                "intento_foto": conv.intento_foto,
                "response_text": MENSAJE_FOTO_POCO_CLARA.format(n=conv.intento_foto),
            }
        # Imagen clara (primer intento) o tercer intento: guardar en Drive, pagos_whatsapp, OCR, pagos_informes, Sheet
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
        # OCR y digitalización (NA si falta campo; link siempre)
        periodo = _periodo_envio_actual()
        fecha_dep = "NA"
        nombre_banco = "NA"
        numero_dep = "NA"
        cantidad = "NA"
        try:
            from app.services.ocr_service import extract_from_image
            ocr_data = extract_from_image(image_bytes)
            fecha_dep = ocr_data.get("fecha_deposito") or "NA"
            nombre_banco = ocr_data.get("nombre_banco") or "NA"
            numero_dep = ocr_data.get("numero_deposito") or "NA"
            cantidad = ocr_data.get("cantidad") or "NA"
        except Exception as e:
            logger.exception("Error OCR: %s", e)
        observacion_informe = conv.observacion or None
        informe = PagosInforme(
            cedula=conv.cedula,
            fecha_deposito=fecha_dep,
            nombre_banco=nombre_banco,
            numero_deposito=numero_dep,
            cantidad=cantidad,
            link_imagen=link_imagen,
            observacion=observacion_informe,
            pagos_whatsapp_id=row_pw.id,
            periodo_envio=periodo,
            fecha_informe=datetime.utcnow(),
        )
        db.add(informe)
        db.commit()
        try:
            from app.services.google_sheets_informe_service import append_row
            sheet_ok = append_row(conv.cedula, fecha_dep, nombre_banco, numero_dep, cantidad, link_imagen, periodo, observacion=observacion_informe)
            if not sheet_ok:
                logger.warning("Sheets: no se escribió la fila. Revisa OAuth conectado, ID hoja y que la hoja esté compartida con la cuenta OAuth.")
        except Exception as e:
            logger.exception("Error escribiendo en Sheet: %s", e)
        cedula_guardada = conv.cedula
        conv.intento_foto = 0
        conv.estado = "esperando_cedula"
        conv.cedula = None
        conv.nombre_cliente = None
        conv.observacion = None
        conv.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "image_saved", "pagos_whatsapp_id": row_pw.id, "cedula_cliente": cedula_guardada, "response_text": MENSAJE_RECIBIDO.format(cedula=cedula_guardada or "N/A")}
