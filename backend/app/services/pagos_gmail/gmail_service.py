"""
Gmail: listar correos (no leidos / leidos / todos) que tienen adjuntos (has:attachment),
descargar solo adjuntos imagen/PDF con filename (sin cuerpo, inline ni HTML),
marcar leido o destacado+no leido segun el pipeline de pagos.
"""
import base64
import logging
import re
import time
from datetime import datetime, timezone
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


# Máximo de segundos que esperamos en un reintento ante 429 (evita bloquear el worker ~15 min).
_GMAIL_429_MAX_WAIT_SECONDS = 120


def _parse_gmail_retry_after_seconds(exc: Exception) -> Optional[int]:
    """
    Parsea 'Retry after 2026-03-10T17:41:45.544Z' del mensaje de error 429 de Gmail.
    Devuelve segundos hasta ese instante, o None si no se puede parsear.
    """
    msg = str(exc) if exc else ""
    # Gmail: "User-rate limit exceeded.  Retry after 2026-03-10T17:41:45.544Z"
    m = re.search(r"Retry\s+after\s+([\dTZ.:+-]+)", msg, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        # ISO 8601 con Z -> reemplazar por +00:00 para fromisoformat
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        retry_at = datetime.fromisoformat(raw)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (retry_at - now).total_seconds()
        return max(0, int(delta))
    except (ValueError, TypeError):
        return None


def list_messages_by_filter(service: Any, filter_type: str = "unread") -> List[dict]:
    """
    Lista mensajes segun el filtro; solo correos con adjuntos (has:attachment).
    "unread" | "read" | "all". Misma forma que antes: id, payload, headers.
    """
    from googleapiclient.errors import HttpError

    def _fetch() -> List[dict]:
        all_msg_refs: List[dict] = []
        page_token: Optional[str] = None
        params_base: dict = {"userId": "me", "maxResults": 500}
        if filter_type == "unread":
            params_base["labelIds"] = ["UNREAD"]
            params_base["q"] = "has:attachment"
        elif filter_type == "read":
            params_base["q"] = "is:read in:inbox has:attachment"
        else:
            params_base["q"] = "in:inbox has:attachment"

        while True:
            params = dict(params_base)
            if page_token:
                params["pageToken"] = page_token
            result = service.users().messages().list(**params).execute()
            batch = result.get("messages", [])
            all_msg_refs.extend(batch)
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        out = []
        for msg in all_msg_refs:
            mid = msg["id"]
            meta = service.users().messages().get(
                userId="me", id=mid, format="metadata", metadataHeaders=["From", "Date", "Subject"]
            ).execute()
            payload = meta.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            out.append({"id": mid, "payload": payload, "headers": headers})
        return out

    try:
        return _fetch()
    except HttpError as e:
        if e.resp.status != 429:
            logger.exception("Gmail list_messages_by_filter(%s): %s", filter_type, e)
            return []
        wait_sec = _parse_gmail_retry_after_seconds(e)
        logger.warning("[PAGOS_GMAIL] Gmail 429 (filtro=%s), esperando %ds, 1 reintento.", filter_type, wait_sec or 0)
        if wait_sec is not None and 0 < wait_sec <= _GMAIL_429_MAX_WAIT_SECONDS:
            time.sleep(wait_sec)
            try:
                return _fetch()
            except HttpError as e2:
                if e2.resp.status == 429:
                    return []
                logger.exception("Gmail list_messages_by_filter (reintento): %s", e2)
                return []
        return []
    except Exception as e:
        logger.exception("Gmail list_messages_by_filter(%s): %s", filter_type, e)
        return []



def count_messages_by_filter(service: Any, filter_type: str = "unread") -> int:
    """
    Cuenta mensajes segun el filtro sin obtener metadata (solo list paginado).
    Mismo criterio que list_messages_by_filter. Util para mostrar N correos a procesar antes de iniciar.
    """
    from googleapiclient.errors import HttpError

    def _count() -> int:
        total = 0
        page_token: Optional[str] = None
        params_base: dict = {"userId": "me", "maxResults": 500}
        if filter_type == "unread":
            params_base["labelIds"] = ["UNREAD"]
            params_base["q"] = "has:attachment"
        elif filter_type == "read":
            params_base["q"] = "is:read in:inbox has:attachment"
        else:
            params_base["q"] = "in:inbox has:attachment"
        while True:
            params = dict(params_base)
            if page_token:
                params["pageToken"] = page_token
            result = service.users().messages().list(**params).execute()
            batch = result.get("messages", [])
            total += len(batch)
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return total

    try:
        return _count()
    except HttpError as e:
        if e.resp.status == 429:
            wait_sec = _parse_gmail_retry_after_seconds(e)
            logger.warning("[PAGOS_GMAIL] Gmail 429 (count, filtro=%s), esperando %ds", filter_type, wait_sec or 0)
            if wait_sec and 0 < wait_sec <= _GMAIL_429_MAX_WAIT_SECONDS:
                time.sleep(wait_sec)
                try:
                    return _count()
                except HttpError:
                    return 0
        logger.warning("Gmail count_messages_by_filter(%s): %s", filter_type, e)
        return 0
    except Exception as e:
        logger.warning("Gmail count_messages_by_filter(%s): %s", filter_type, e)
        return 0


def list_unread_with_attachments(service: Any) -> List[dict]:
    """
    Lista TODOS los mensajes NO LEÍDOS (equivalente a list_messages_by_filter(service, "unread")).
    Mantenido por compatibilidad; el pipeline puede usar list_messages_by_filter con scan_filter.
    """
    return list_messages_by_filter(service, "unread")


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


def _html_to_plain(html: str) -> str:
    """Convierte HTML a texto plano para uso en extracción (cuerpo del correo)."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub(r"&lt;", "<", text, flags=re.IGNORECASE)
    text = re.sub(r"&gt;", ">", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_message_body_text(payload: dict) -> str:
    """
    Extrae el cuerpo del correo en texto plano desde el payload de Gmail API.
    Prefiere text/plain; si no hay, usa text/html convirtiendo a texto.
    Útil para que Gemini extraiga datos del cuerpo cuando no hay adjuntos o como contexto.
    """
    plain = ""
    html = ""

    def _collect(part: dict) -> None:
        nonlocal plain, html
        mime = (part.get("mimeType") or "").strip().lower()
        body = part.get("body") or {}
        data_b64 = body.get("data")
        if not data_b64:
            for sub in (part.get("parts") or []):
                _collect(sub)
            return
        try:
            raw = base64.urlsafe_b64decode(data_b64 + "==")
            text = raw.decode("utf-8", errors="replace")
            if mime == "text/plain":
                plain = text
            elif mime == "text/html" and not plain:
                html = text
        except Exception:
            pass
        for sub in (part.get("parts") or []):
            _collect(sub)

    _collect(payload)
    if plain:
        return plain.strip()[:15000]  # límite razonable para contexto Gemini
    if html:
        return _html_to_plain(html).strip()[:15000]
    return ""


def get_message_raw_bytes(service: Any, message_id: str) -> Optional[bytes]:
    """
    Obtiene el correo completo en formato raw (RFC 2822) para guardarlo como .eml en Drive.
    Returns bytes del mensaje .eml o None si falla.
    """
    try:
        msg = service.users().messages().get(userId="me", id=message_id, format="raw").execute()
        raw_b64 = msg.get("raw")
        if not raw_b64:
            return None
        # Gmail devuelve base64url; añadir padding si hace falta
        pad = 4 - len(raw_b64) % 4
        if pad != 4:
            raw_b64 += "=" * pad
        return base64.urlsafe_b64decode(raw_b64)
    except Exception as e:
        logger.warning("Error obteniendo mensaje raw %s: %s", message_id, e)
        return None


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


def get_attachment_image_pdf_files_for_message(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Solo archivos adjuntos reales (filename + attachmentId), recorriendo multiparte.
    Incluye solo tipos imagen/PDF permitidos (MIME_IMAGE_OR_PDF). No inline sin nombre,
    no imagenes del cuerpo HTML, no message/rfc822 incrustado.
    """
    out: List[Tuple[str, bytes, str]] = []

    def walk(parts: List[dict]) -> None:
        for part in parts:
            nested = part.get("parts") or []
            if nested:
                walk(nested)
                continue
            filename = (part.get("filename") or "").strip()
            if not filename or not is_allowed_attachment(filename):
                continue
            mime = (part.get("mimeType") or "application/octet-stream").strip().lower()
            if mime not in MIME_IMAGE_OR_PDF:
                continue
            att_id = part.get("body", {}).get("attachmentId")
            if not att_id:
                continue
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                data = att.get("data")
                if data:
                    raw = base64.urlsafe_b64decode(data)
                    out.append((filename, raw, mime))
            except Exception as e:
                logger.warning("Error descargando adjunto %s: %s", filename, e)

    parts = payload.get("parts") or []
    if parts:
        walk(parts)
    else:
        mime = (payload.get("mimeType") or "").strip().lower()
        fn = (payload.get("filename") or "").strip()
        body = payload.get("body") or {}
        att_id = body.get("attachmentId")
        if fn and att_id and mime in MIME_IMAGE_OR_PDF and is_allowed_attachment(fn):
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                data = att.get("data")
                if data:
                    raw = base64.urlsafe_b64decode(data)
                    out.append((fn, raw, mime))
            except Exception as e:
                logger.warning("Error descargando adjunto raiz %s: %s", fn, e)
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


def _min_payment_image_bytes() -> int:
    """Umbral minimo de bytes en get_all_images (legacy); 0 = no filtrar por tamano."""
    from app.core.config import settings
    return int(getattr(settings, "PAGOS_GMAIL_MIN_IMAGE_BYTES", 0) or 0)


def get_all_images_and_files_for_message(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Extrae imágenes/PDFs de todas las fuentes posibles del mensaje:
    1. Adjuntos directos (imagen/PDF adjunto al email).
    2. Partes inline MIME (Content-Disposition: inline).
    3. Imágenes base64 embebidas en HTML del cuerpo.
    4. Mensajes reenviados (message/rfc822 / Fwd:) — el comprobante está dentro del .eml adjunto.
    Filtra por tamano si _min_payment_image_bytes() > 0. Devuelve (filename, content_bytes, mime_type) sin duplicados.
    """
    min_bytes = _min_payment_image_bytes()
    seen: set = set()
    out: List[Tuple[str, bytes, str]] = []

    def _add(items: List[Tuple[str, bytes, str]]) -> None:
        for filename, content, mime in items:
            size = len(content)
            if size < min_bytes:
                logger.warning("[PAGOS_GMAIL] Descartada (< %d bytes): %s (%d bytes)", min_bytes, filename, size)
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
        logger.warning("[PAGOS_GMAIL] CERO imágenes >= %d bytes para msg %s — todo descartado o correo sin imágenes", min_bytes, message_id)
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


def mark_read_and_clear_star(service: Any, message_id: str) -> None:
    """Quita UNREAD y STARRED (comprobante reconocido y procesado)."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD", "STARRED"]},
        ).execute()
    except Exception as e:
        logger.warning("Error mark_read_and_clear_star %s: %s", message_id, e)


def mark_starred_and_unread(service: Any, message_id: str) -> None:
    """Destaca el mensaje y lo deja como no leido (formato no reconocido o sin datos procesables)."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["STARRED", "UNREAD"]},
        ).execute()
    except Exception as e:
        logger.warning("Error mark_starred_and_unread %s: %s", message_id, e)
