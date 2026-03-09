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
    subject_contains_email,
)

logger = logging.getLogger(__name__)


def build_gmail_service(credentials: Any):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _message_has_extractable_content(payload: dict) -> bool:
    """True si el mensaje tiene adjuntos permitidos o partes imagen/PDF (incl. inline en cuerpo)."""
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
        nested = part.get("parts") or []
        if nested and _message_has_extractable_content({"parts": nested}):
            return True
    return False


def list_unread_with_attachments(service: Any) -> List[dict]:
    """
    Lista mensajes no leídos que: (1) tengan al menos un adjunto permitido O imagen/PDF en el cuerpo,
    y (2) el Asunto contenga una dirección de email. Si el Asunto no tiene email, el mensaje no se toma en cuenta.
    """
    try:
        result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=100).execute()
        messages = result.get("messages", [])
        out = []
        for msg in messages:
            mid = msg["id"]
            meta = service.users().messages().get(
                userId="me", id=mid, format="metadata", metadataHeaders=["From", "Date", "Subject"]
            ).execute()
            payload = meta.get("payload", {})
            if not _message_has_extractable_content(payload):
                continue
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            subject = headers.get("subject", "")
            if not subject_contains_email(subject):
                continue
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


def get_all_images_and_files_for_message(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Todos los archivos/imágenes a procesar: adjuntos permitidos + imágenes inline (MIME) + imágenes en cuerpo HTML.
    Returns (filename, content_bytes, mime_type). Sin duplicados por (filename, size) cuando sea posible.
    """
    seen = set()
    out = []
    for filename, content, mime in get_attachments_for_message(service, message_id, payload):
        key = (filename, len(content))
        if key not in seen:
            seen.add(key)
            out.append((filename, content, mime))
    for filename, content, mime in _get_inline_images_from_parts(service, message_id, payload.get("parts", [])):
        key = (filename, len(content))
        if key not in seen:
            seen.add(key)
            out.append((filename, content, mime))
    for filename, content, mime in _get_images_from_html_body(service, message_id, payload):
        key = (filename, len(content))
        if key not in seen:
            seen.add(key)
            out.append((filename, content, mime))
    return out


def mark_as_read(service: Any, message_id: str) -> None:
    try:
        service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    except Exception as e:
        logger.warning("Error marcando mensaje %s como leído: %s", message_id, e)
