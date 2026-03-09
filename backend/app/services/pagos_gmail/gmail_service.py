"""
Gmail: listar no leídos con adjuntos o imágenes en cuerpo, extraer fecha + remitente,
descargar adjuntos e imágenes inline (MIME o HTML base64), marcar como leído.
"""
import base64
import logging
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    ext_for_mime,
    is_allowed_attachment,
    MIME_IMAGE_OR_PDF,
)

logger = logging.getLogger(__name__)


def build_gmail_service(credentials: Any):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _message_has_extractable_content(payload: dict) -> bool:
    """
    True si el mensaje tiene adjuntos permitidos, imágenes/PDF en el cuerpo,
    o un mensaje reenviado (message/rfc822) que puede contener comprobantes dentro.
    """
    parts = payload.get("parts", [])
    if not parts:
        mime = (payload.get("mimeType") or "").lower()
        if mime in MIME_IMAGE_OR_PDF and (payload.get("body", {}).get("data") or payload.get("body", {}).get("attachmentId")):
            return True
        if payload.get("filename") and is_allowed_attachment(payload.get("filename", "")):
            return True
        return False
    for part in parts:
        filename = (part.get("filename") or "").strip()
        if filename and is_allowed_attachment(filename):
            return True
        mime = (part.get("mimeType") or "").strip().lower()
        if mime in MIME_IMAGE_OR_PDF:
            return True
        # Correo reenviado (Fwd:): el comprobante está dentro del mensaje adjunto
        if mime == "message/rfc822":
            return True
        nested = part.get("parts") or []
        if nested and _message_has_extractable_content({"parts": nested}):
            return True
    return False


def list_unread_with_attachments(service: Any) -> List[dict]:
    """
    Lista TODOS los mensajes NO LEÍDOS. No filtra por contenido: el filtro de metadata
    (format="metadata") no devuelve partes anidadas, por lo que correos Fwd: con imágenes
    dentro de message/rfc822 serían excluidos erróneamente. En cambio, el pipeline procesa
    cada correo (obteniendo el payload completo), extrae lo que encuentra y, si no hay
    imágenes, guarda una fila NA. Todos se marcan como leídos al finalizar.
    """
    try:
        result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=500).execute()
        messages = result.get("messages", [])
        out = []
        for msg in messages:
            mid = msg["id"]
            meta = service.users().messages().get(
                userId="me", id=mid, format="metadata", metadataHeaders=["From", "Date", "Subject"]
            ).execute()
            payload = meta.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            out.append({"id": mid, "payload": payload, "headers": headers})
        return out
    except Exception as e:
        logger.exception("Gmail list_unread_with_attachments: %s", e)
        return []


def get_message_date(headers: dict) -> datetime:
    """Fecha de recepción del correo (para carpeta/hoja por día)."""
    from email.utils import parsedate_to_datetime
    date_str = headers.get("date") or headers.get("Date") or ""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return datetime.utcnow()


def get_message_full_payload(service: Any, message_id: str) -> dict:
    """Obtiene el payload completo del mensaje (incluye body.data para partes inline y HTML)."""
    try:
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        return msg.get("payload", {})
    except Exception as e:
        logger.warning("Error obteniendo mensaje completo %s: %s", message_id, e)
        return {}


def get_attachments_for_message(service: Any, message_id: str, payload: dict) -> List[Tuple[str, bytes, str]]:
    """(filename, content_bytes, mime_type) para cada adjunto permitido."""
    parts = payload.get("parts", [])
    out = []
    for part in parts:
        filename = (part.get("filename") or "").strip()
        if not filename or not is_allowed_attachment(filename):
            continue
        att_id = part.get("body", {}).get("attachmentId")
        if not att_id:
            continue
        try:
            att = service.users().messages().attachments().get(userId="me", messageId=message_id, id=att_id).execute()
            data = att.get("data")
            if data:
                raw = base64.urlsafe_b64decode(data)
                mime = part.get("mimeType") or "application/octet-stream"
                out.append((filename, raw, mime))
        except Exception as e:
            logger.warning("Error descargando adjunto %s: %s", filename, e)
    return out


def _get_inline_images_from_parts(
    service: Any, message_id: str, parts: List[dict], prefix: str = ""
) -> List[Tuple[str, bytes, str]]:
    """Recorre parts y devuelve (filename, content, mime) para partes imagen/PDF con body.data o attachmentId."""
    out = []
    for i, part in enumerate(parts):
        mime = (part.get("mimeType") or "").strip().lower()
        nested = part.get("parts") or []
        if nested:
            out.extend(_get_inline_images_from_parts(service, message_id, nested, prefix=f"{prefix}{i}_"))
            continue
        if mime not in MIME_IMAGE_OR_PDF:
            continue
        body = part.get("body") or {}
        att_id = body.get("attachmentId")
        data_b64 = body.get("data")
        raw = None
        if data_b64:
            try:
                raw = base64.urlsafe_b64decode(data_b64)
            except Exception as e:
                logger.debug("Decode inline part %s: %s", prefix, e)
        elif att_id:
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                if att.get("data"):
                    raw = base64.urlsafe_b64decode(att["data"])
            except Exception as e:
                logger.warning("Error descargando parte inline %s: %s", att_id, e)
        if raw:
            filename = (part.get("filename") or "").strip()
            if not filename:
                filename = f"inline_{prefix}{i}.{ext_for_mime(mime)}"
            out.append((filename, raw, mime))
    return out


def _get_images_from_html_body(service: Any, message_id: str, payload: dict) -> List[Tuple[str, bytes, str]]:
    """Extrae imágenes embebidas en HTML como data:image/...;base64,..."""
    out = []
    parts = payload.get("parts", [])
    html_parts = []
    for part in parts:
        mime = (part.get("mimeType") or "").strip().lower()
        if mime == "text/html":
            body = part.get("body") or {}
            if body.get("data"):
                try:
                    html_parts.append(base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace"))
                except Exception as e:
                    logger.debug("Decode HTML part: %s", e)
            elif body.get("attachmentId"):
                try:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=message_id, id=body["attachmentId"]
                    ).execute()
                    if att.get("data"):
                        html_parts.append(base64.urlsafe_b64decode(att["data"]).decode("utf-8", errors="replace"))
                except Exception as e:
                    logger.debug("Fetch HTML attachment: %s", e)
    # También cuerpo sin parts
    if not html_parts and payload.get("mimeType", "").strip().lower() == "text/html":
        body = payload.get("body") or {}
        if body.get("data"):
            try:
                html_parts.append(base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace"))
            except Exception:
                pass
    # Regex: data:image/(jpeg|png|...);base64,([A-Za-z0-9+/=]+)
    data_url_re = re.compile(r"data:image/([a-zA-Z0-9+.-]+);base64,([A-Za-z0-9+/=]+)")
    for idx, html in enumerate(html_parts):
        for m in data_url_re.finditer(html):
            try:
                subtype = m.group(1).lower().replace("+", "-")
                b64 = m.group(2)
                raw = base64.b64decode(b64)
                mime = f"image/{subtype}" if "/" in subtype else f"image/{subtype}"
                if mime == "image/jpg":
                    mime = "image/jpeg"
                out.append((f"body_image_{idx}_{len(out)}.{ext_for_mime(mime)}", raw, mime))
            except Exception as e:
                logger.debug("Decode data URL image: %s", e)
    return out


def _get_images_from_rfc822_parts(
    service: Any, message_id: str, parts: List[dict], prefix: str = ""
) -> List[Tuple[str, bytes, str]]:
    """
    Extrae imágenes/PDFs de partes message/rfc822 (correos reenviados, "Fwd:").
    Descarga el .eml adjunto y usa el módulo email de Python para recorrer sus partes.
    """
    import email as email_lib
    out = []
    for i, part in enumerate(parts):
        mime = (part.get("mimeType") or "").strip().lower()
        if mime != "message/rfc822":
            continue
        body = part.get("body") or {}
        att_id = body.get("attachmentId")
        data_b64 = body.get("data")
        raw: bytes | None = None
        if data_b64:
            try:
                raw = base64.urlsafe_b64decode(data_b64)
            except Exception as e:
                logger.debug("Decode rfc822 inline %s: %s", prefix, e)
        elif att_id:
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                if att.get("data"):
                    raw = base64.urlsafe_b64decode(att["data"])
            except Exception as e:
                logger.warning("Error descargando rfc822 %s: %s", att_id, e)
        if not raw:
            continue
        # Parsear el .eml y extraer imágenes/PDFs dentro
        try:
            embedded_msg = email_lib.message_from_bytes(raw)
            for j, subpart in enumerate(embedded_msg.walk()):
                ct = (subpart.get_content_type() or "").lower()
                if ct not in MIME_IMAGE_OR_PDF:
                    continue
                payload_bytes = subpart.get_payload(decode=True)
                if not payload_bytes:
                    continue
                fname = subpart.get_filename() or f"fwd_{prefix}{i}_{j}.{ext_for_mime(ct)}"
                out.append((fname, payload_bytes, ct))
                logger.debug("[PAGOS_GMAIL] rfc822: imagen extraída '%s' (%s, %d bytes)", fname, ct, len(payload_bytes))
        except Exception as e:
            logger.warning("Error parseando rfc822 %s: %s", prefix, e)
    return out


# Imágenes menores a este umbral son casi siempre logos, íconos o decoraciones de plantilla
# de correo, no comprobantes de pago. 10 KB es un límite conservador seguro.
MIN_PAYMENT_IMAGE_BYTES = 10_240  # 10 KB


def get_all_images_and_files_for_message(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Extrae imágenes/PDFs de todas las fuentes posibles del mensaje:
    1. Adjuntos directos (imagen/PDF adjunto al email).
    2. Partes inline MIME (Content-Disposition: inline).
    3. Imágenes base64 embebidas en HTML del cuerpo.
    4. Mensajes reenviados (message/rfc822 / Fwd:) — el comprobante está dentro del .eml adjunto.
    Filtra imágenes < 10 KB (logos/decoraciones). Devuelve (filename, content_bytes, mime_type) sin duplicados.
    """
    seen: set = set()
    out: List[Tuple[str, bytes, str]] = []

    def _add(items: List[Tuple[str, bytes, str]]) -> None:
        for filename, content, mime in items:
            size = len(content)
            if size < MIN_PAYMENT_IMAGE_BYTES:
                logger.warning("[PAGOS_GMAIL] Descartada (< 10KB): %s (%d bytes)", filename, size)
                continue
            key = (filename, size)
            if key not in seen:
                seen.add(key)
                logger.warning("[PAGOS_GMAIL] Aceptada: %s (%d bytes, %s)", filename, size, mime)
                out.append((filename, content, mime))

    _add(get_attachments_for_message(service, message_id, payload))
    _add(_get_inline_images_from_parts(service, message_id, payload.get("parts", [])))
    _add(_get_images_from_html_body(service, message_id, payload))
    _add(_get_images_from_rfc822_parts(service, message_id, payload.get("parts", [])))

    if not out:
        logger.warning("[PAGOS_GMAIL] CERO imágenes >= 10KB para msg %s — todo descartado o correo sin imágenes", message_id)
    return out


def extract_forwarded_sender(full_payload: dict) -> Optional[str]:
    """
    Extrae el remitente original de un mensaje reenviado buscando la línea
    'De: NAME <email>' o 'From: NAME <email>' después del marcador
    '---------- Forwarded message ----------' en el cuerpo de texto plano.
    También busca en partes message/rfc822 el header From del mensaje incrustado.
    Devuelve la cadena 'NAME <email>' o solo 'email' si se encuentra, None si no.
    """
    # 1. Intentar con message/rfc822: extraer From del .eml incrustado
    import email as email_lib

    def _find_rfc822_from(parts: list) -> Optional[str]:
        for part in parts:
            mime = (part.get("mimeType") or "").strip().lower()
            if mime == "message/rfc822":
                body = part.get("body") or {}
                data_b64 = body.get("data")
                if data_b64:
                    try:
                        raw = base64.urlsafe_b64decode(data_b64 + "==")
                        msg = email_lib.message_from_bytes(raw)
                        return msg.get("From") or msg.get("from")
                    except Exception:
                        pass
            nested = part.get("parts") or []
            if nested:
                found = _find_rfc822_from(nested)
                if found:
                    return found
        return None

    rfc_from = _find_rfc822_from(full_payload.get("parts") or [])
    if rfc_from:
        return rfc_from.strip()

    # 2. Fallback: parsear el texto plano buscando el marcador de reenvío
    def _get_plain_text(p: dict) -> str:
        mime = (p.get("mimeType") or "").lower()
        if mime == "text/plain":
            data = (p.get("body") or {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                except Exception:
                    pass
        for sub in (p.get("parts") or []):
            result = _get_plain_text(sub)
            if result:
                return result
        return ""

    text = _get_plain_text(full_payload)
    if text:
        # Buscar después del marcador de reenvío
        marker = re.search(r"-{5,}\s*Forwarded message\s*-{5,}", text, re.IGNORECASE)
        search_text = text[marker.end():] if marker else text
        # "De: NOMBRE <email>" o "From: NOMBRE <email>"
        m = re.search(r"(?:De|From):\s+(.*?<[^>]+@[^>]+>)", search_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Sin ángulos: "De: email@dominio.com"
        m = re.search(r"(?:De|From):\s+([^\s<@,\n]+@[^\s,\n]+)", search_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return None


def mark_as_read(service: Any, message_id: str) -> None:
    """Marca el mensaje como leído en Gmail (quita UNREAD). No se volverá a leer ni a procesar; evita reprocesar desde cero."""
    try:
        service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    except Exception as e:
        logger.warning("Error marcando mensaje %s como leído: %s", message_id, e)
