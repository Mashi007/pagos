"""
Gmail: listar no leídos con adjuntos permitidos, extraer fecha + remitente, descargar adjunto, marcar como leído.
"""
import base64
import logging
from datetime import datetime
from typing import Any, List, Optional, Tuple

from app.services.pagos_gmail.helpers import extract_sender_email, is_allowed_attachment

logger = logging.getLogger(__name__)


def build_gmail_service(credentials: Any):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def list_unread_with_attachments(service: Any) -> List[dict]:
    """Lista IDs de mensajes no leídos que tengan al menos un adjunto permitido."""
    try:
        result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=100).execute()
        messages = result.get("messages", [])
        out = []
        for msg in messages:
            mid = msg["id"]
            meta = service.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=["From", "Date"]).execute()
            payload = meta.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            parts = payload.get("parts", [])
            has_allowed = False
            for part in parts:
                filename = (part.get("filename") or "").strip()
                if filename and is_allowed_attachment(filename):
                    has_allowed = True
                    break
            if not parts and payload.get("filename") and is_allowed_attachment(payload.get("filename", "")):
                has_allowed = True
            if has_allowed:
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


def mark_as_read(service: Any, message_id: str) -> None:
    try:
        service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    except Exception as e:
        logger.warning("Error marcando mensaje %s como leído: %s", message_id, e)
