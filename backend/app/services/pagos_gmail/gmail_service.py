"""
Gmail: listar correos con adjunto o parte con nombre de imagen/PDF (has:attachment OR filename:png|jpg|...).
Pipeline Pagos: toda imagen/PDF util (archivo adjunto o incrustada en cuerpo/related/HTML/mixed), mas .eml rfc822;
deduplicado por contenido. La plantilla imagen 1/2/3/4 la decide solo Gemini al escanear cada binario.
"""
import base64
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    ext_for_mime,
    is_allowed_attachment,
    MIME_IMAGE_OR_PDF,
)

logger = logging.getLogger(__name__)

# Etiquetas de usuario (A = MERCANTIL, B = BNC, C = BINANCE, D = BNV / BDV). Se crean si no existen.
PAGOS_GMAIL_LABEL_IMAGEN_1 = "MERCANTIL"
PAGOS_GMAIL_LABEL_IMAGEN_2 = "BNC"
PAGOS_GMAIL_LABEL_IMAGEN_3 = "BINANCE"
PAGOS_GMAIL_LABEL_IMAGEN_4 = "BNV"
# Remitente fijo master@rapicreditca.com: solo esta etiqueta en Gmail (no MERCANTIL / BNC / BINANCE / BNV ni ERROR EMAIL). Ver pipeline.
PAGOS_GMAIL_LABEL_IMAGEN_5 = "IMAGEN 5"
# Remitente (De) sin fila en clientes.email (o fallo BD): misma leyenda que columna Cedula del Excel.
PAGOS_GMAIL_LABEL_ERROR_EMAIL = "ERROR EMAIL"
# Ninguna plantilla A/B/C/D reconocida (o no se aplico otra etiqueta de clasificacion).
PAGOS_GMAIL_LABEL_MANUAL = "MANUAL"


def pagos_gmail_label_exclusions_query() -> str:
    """
    Fragmento para el parametro q de Gmail: excluye correos ya clasificados por el pipeline
    (no volver a escanear si tienen MERCANTIL / BNC / BINANCE / BNV / IMAGEN 5 / ERROR EMAIL / MANUAL).
    """
    return (
        f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_1}" '
        f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_2}" '
        f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_3}" '
        f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_4}" '
        f'-label:"{PAGOS_GMAIL_LABEL_IMAGEN_5}" '
        f'-label:"{PAGOS_GMAIL_LABEL_ERROR_EMAIL}" '
        f'-label:"{PAGOS_GMAIL_LABEL_MANUAL}"'
    )


def pagos_gmail_list_q_media_parts() -> str:
    """
    Criterio Gmail: adjunto declarado O parte con nombre de imagen/PDF (capturas en cuerpo / inline).
    Evita perder Binance y similares que no disparan has:attachment en algunos clientes.
    """
    return (
        "(has:attachment OR filename:png OR filename:jpg OR filename:jpeg OR "
        "filename:pdf OR filename:webp OR filename:heic OR filename:gif)"
    )


def pagos_gmail_pending_identification_query() -> str:
    """
    Consulta Gmail (parametro q): inbox, con adjunto o imagen en cuerpo, sin estrella, sin etiquetas de clasificacion.
    Asi el escaneo periodico no reprocesa correos ya marcados con MERCANTIL / BNC / BINANCE / BNV / IMAGEN 5 / ERROR EMAIL / MANUAL o destacados.
    """
    return (
        f"in:inbox -is:starred {pagos_gmail_list_q_media_parts()} "
        f"{pagos_gmail_label_exclusions_query()}"
    )


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
    Lista mensajes segun el filtro; correos con adjunto o parte imagen/PDF nombrada (inline/cuerpo).
    filter_type: "unread" | "read" | "all" | "pending_identification".
    Todos los filtros excluyen por q los correos con etiquetas de clasificacion del pipeline (no reescanear).
    pending_identification: ademas sin estrella (reintento cola sin reprocesar ya clasificados).
    Misma forma que antes: id, payload, headers.
    """
    from googleapiclient.errors import HttpError

    def _fetch() -> List[dict]:
        all_msg_refs: List[dict] = []
        page_token: Optional[str] = None
        params_base: dict = {"userId": "me", "maxResults": 500}
        media_q = pagos_gmail_list_q_media_parts()
        excl = pagos_gmail_label_exclusions_query()
        if filter_type == "unread":
            params_base["labelIds"] = ["UNREAD"]
            params_base["q"] = f"in:inbox {media_q} {excl}"
        elif filter_type == "read":
            params_base["q"] = f"is:read in:inbox {media_q} {excl}"
        elif filter_type == "pending_identification":
            params_base["q"] = pagos_gmail_pending_identification_query()
        else:
            params_base["q"] = f"in:inbox {media_q} {excl}"

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
    Mismo criterio que list_messages_by_filter (incluye pending_identification).
    """
    from googleapiclient.errors import HttpError

    def _count() -> int:
        total = 0
        page_token: Optional[str] = None
        params_base: dict = {"userId": "me", "maxResults": 500}
        media_q = pagos_gmail_list_q_media_parts()
        excl = pagos_gmail_label_exclusions_query()
        if filter_type == "unread":
            params_base["labelIds"] = ["UNREAD"]
            params_base["q"] = f"in:inbox {media_q} {excl}"
        elif filter_type == "read":
            params_base["q"] = f"is:read in:inbox {media_q} {excl}"
        elif filter_type == "pending_identification":
            params_base["q"] = pagos_gmail_pending_identification_query()
        else:
            params_base["q"] = f"in:inbox {media_q} {excl}"
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
    Partes imagen/PDF con attachmentId (adjunto archivo tipico o parte descargable).
    Si Gmail no envia filename o la extension no coincide, se usa nombre sintetico para no perder el binario.
    El pipeline Pagos combina esto con cuerpo incrustado en get_pagos_gmail_image_pdf_files_for_pipeline.
    """
    out: List[Tuple[str, bytes, str]] = []

    def _effective_filename(part: dict, mime: str, att_id: str) -> str:
        fn = (part.get("filename") or "").strip()
        if fn and is_allowed_attachment(fn):
            return fn
        safe = (att_id or "x").replace("/", "_")[:20]
        return f"gmail_att_{safe}.{ext_for_mime(mime)}"

    def walk(parts: List[dict]) -> None:
        for part in parts:
            nested = part.get("parts") or []
            if nested:
                walk(nested)
                continue
            mime = (part.get("mimeType") or "application/octet-stream").strip().lower()
            if mime not in MIME_IMAGE_OR_PDF:
                continue
            att_id = part.get("body", {}).get("attachmentId")
            if not att_id:
                continue
            use_fn = _effective_filename(part, mime, att_id)
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                data = att.get("data")
                if data:
                    raw = base64.urlsafe_b64decode(data)
                    out.append((use_fn, raw, mime))
            except Exception as e:
                logger.warning("Error descargando adjunto %s: %s", use_fn, e)

    parts = payload.get("parts") or []
    if parts:
        walk(parts)
    else:
        mime = (payload.get("mimeType") or "").strip().lower()
        body = payload.get("body") or {}
        att_id = body.get("attachmentId")
        if att_id and mime in MIME_IMAGE_OR_PDF:
            use_fn = _effective_filename(payload, mime, att_id)
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id
                ).execute()
                data = att.get("data")
                if data:
                    raw = base64.urlsafe_b64decode(data)
                    out.append((use_fn, raw, mime))
            except Exception as e:
                logger.warning("Error descargando adjunto raiz %s: %s", use_fn, e)
    return out


def _header_value_from_part_headers(part: dict, header_name: str) -> str:
    want = header_name.strip().lower()
    for h in part.get("headers") or []:
        if (h.get("name") or "").strip().lower() == want:
            return (h.get("value") or "").strip()
    return ""


def _content_disposition_type(cd_value: str) -> str:
    """Primer token de Content-Disposition: inline, attachment, form-data, o vacio."""
    if not (cd_value or "").strip():
        return ""
    return (cd_value.split(";", 1)[0].strip().lower())


def _download_gmail_leaf_part_bytes(service: Any, message_id: str, part: dict) -> Optional[bytes]:
    body = part.get("body") or {}
    data_b64 = body.get("data")
    if data_b64:
        try:
            return base64.urlsafe_b64decode(data_b64)
        except Exception as e:
            logger.debug("Decode part data: %s", e)
            return None
    att_id = body.get("attachmentId")
    if not att_id:
        return None
    try:
        att = service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=att_id
        ).execute()
        if att.get("data"):
            return base64.urlsafe_b64decode(att["data"])
    except Exception as e:
        logger.warning("Error descargando attachmentId %s: %s", att_id, e)
    return None


def _is_body_embedded_image_pdf_leaf(part: dict, parent_mime: str) -> bool:
    """
    True: inline, multipart/related (cid), o hijo de multipart/mixed sin disposition attachment
    (imagen en el cuerpo del correo junto al texto). False si es explicitamente attachment
    (lo cubre get_attachment_image_pdf_files_for_message; dedupe evita doble escaneo).
    """
    dt = _content_disposition_type(_header_value_from_part_headers(part, "Content-Disposition"))
    if dt == "attachment":
        return False
    if dt == "inline":
        return True
    p = (parent_mime or "").strip().lower()
    if p == "multipart/related":
        return True
    if p == "multipart/mixed":
        return True
    return False


def _dedupe_image_pdf_by_content(items: List[Tuple[str, bytes, str]]) -> List[Tuple[str, bytes, str]]:
    seen: set[str] = set()
    out: List[Tuple[str, bytes, str]] = []
    for fn, content, mime in items:
        fp = hashlib.sha256(content).hexdigest()
        if fp in seen:
            continue
        seen.add(fp)
        out.append((fn, content, mime))
    return out


def get_body_embedded_image_pdf_files_for_message(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Imagenes/PDF mostradas en el cuerpo del correo (no como attachment declarado):
    - Content-Disposition: inline, multipart/related (cid), multipart/mixed sin attachment,
    - data:image/...;base64,... en HTML,
    - mensaje de una sola parte image/* o PDF sin Content-Disposition: attachment.
    """
    out: List[Tuple[str, bytes, str]] = []
    parts = payload.get("parts") or []

    def _append_leaf(part: dict, mime: str) -> None:
        if mime not in MIME_IMAGE_OR_PDF:
            return
        raw = _download_gmail_leaf_part_bytes(service, message_id, part)
        if not raw:
            return
        fn = (part.get("filename") or "").strip()
        if not fn or not is_allowed_attachment(fn):
            fn = f"inline_body.{ext_for_mime(mime)}"
        out.append((fn, raw, mime))

    if not parts:
        root_mime = (payload.get("mimeType") or "").strip().lower()
        if root_mime in MIME_IMAGE_OR_PDF:
            if _content_disposition_type(_header_value_from_part_headers(payload, "Content-Disposition")) != "attachment":
                _append_leaf(payload, root_mime)
    else:

        def walk(plist: List[dict], parent_mime: str) -> None:
            for part in plist:
                mime = (part.get("mimeType") or "").strip().lower()
                nested = part.get("parts") or []
                if nested:
                    walk(nested, mime)
                    continue
                if mime not in MIME_IMAGE_OR_PDF:
                    continue
                if not _is_body_embedded_image_pdf_leaf(part, parent_mime):
                    continue
                _append_leaf(part, mime)

        walk(parts, (payload.get("mimeType") or "").strip().lower())

    try:
        out.extend(_get_images_from_html_body(service, message_id, payload))
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] get_body_embedded: HTML body images: %s", e)

    return _dedupe_image_pdf_by_content(out)


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
    Extrae imagenes/PDFs de partes message/rfc822 (correos reenviados, Fwd:).
    Recorre el arbol de parts en profundidad; parsea cada .eml con email.message.
    """
    import email as email_lib

    out: List[Tuple[str, bytes, str]] = []
    for i, part in enumerate(parts):
        mime = (part.get("mimeType") or "").strip().lower()
        nested = part.get("parts") or []
        if nested:
            out.extend(
                _get_images_from_rfc822_parts(
                    service, message_id, nested, prefix=f"{prefix}{i}_"
                )
            )
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
                logger.debug(
                    "[PAGOS_GMAIL] rfc822: extraido '%s' (%s, %d bytes)",
                    fname,
                    ct,
                    len(payload_bytes),
                )
        except Exception as e:
            logger.warning("Error parseando rfc822 %s: %s", prefix, e)
    return out


def get_pagos_gmail_image_pdf_files_for_pipeline(
    service: Any, message_id: str, payload: dict
) -> List[Tuple[str, bytes, str]]:
    """
    Candidatos a escanear con Gemini (misma imagen adjunta o en cuerpo se deduplica por hash SHA-256):
    1) Incrustado en cuerpo: inline, multipart/related (cid), data: en HTML, hijos image/PDF en multipart/mixed
       que no sean Content-Disposition: attachment.
    2) Archivo adjunto: cualquier parte image/PDF con attachmentId (con o sin filename en Gmail).
    3) Reenvios: binarios image/PDF dentro de message/rfc822 (.eml anidado).
    4) Recorrido MIME completo: todas las partes image/PDF con body.data o attachmentId (cubre p. ej. hijos de
       multipart/alternative que 1) no marcaria solo como \"cuerpo\"). Duplicados respecto a 1–3 se eliminan al deduplicar.
    Solo pasan a BD/Drive si el modelo devuelve plantilla A/B/C y datos completos.
    """
    embedded = get_body_embedded_image_pdf_files_for_message(service, message_id, payload)
    attached = get_attachment_image_pdf_files_for_message(service, message_id, payload)
    rfc822_parts: List[Tuple[str, bytes, str]] = []
    try:
        rfc822_parts = _get_images_from_rfc822_parts(
            service, message_id, payload.get("parts", [])
        )
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] rfc822 en pipeline: %s", e)

    part_roots: List[dict] = list(payload.get("parts") or [])
    if not part_roots:
        mime_root = (payload.get("mimeType") or "").strip().lower()
        if mime_root in MIME_IMAGE_OR_PDF:
            part_roots = [payload]
    mime_walk = (
        _get_inline_images_from_parts(service, message_id, part_roots)
        if part_roots
        else []
    )

    merged: List[Tuple[str, bytes, str]] = []
    merged.extend(embedded)
    merged.extend(attached)
    merged.extend(rfc822_parts)
    merged.extend(mime_walk)
    unique = _dedupe_image_pdf_by_content(merged)
    logger.debug(
        "[PAGOS_GMAIL] msg %s candidatos (pre-dedupe): incrustados=%d adjuntos=%d rfc822=%d mime_completo=%d -> unicos=%d",
        message_id,
        len(embedded),
        len(attached),
        len(rfc822_parts),
        len(mime_walk),
        len(unique),
    )
    return unique


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
                logger.debug("[PAGOS_GMAIL] Descartada (< %d bytes): %s (%d bytes)", min_bytes, filename, size)
                continue
            key = (filename, size)
            if key not in seen:
                seen.add(key)
                logger.debug("[PAGOS_GMAIL] Aceptada: %s (%d bytes, %s)", filename, size, mime)
                out.append((filename, content, mime))

    _add(get_attachments_for_message(service, message_id, payload))
    _add(_get_inline_images_from_parts(service, message_id, payload.get("parts", [])))
    _add(_get_images_from_html_body(service, message_id, payload))
    _add(_get_images_from_rfc822_parts(service, message_id, payload.get("parts", [])))

    if not out:
        logger.info("[PAGOS_GMAIL] CERO imagenes >= %d bytes para msg %s - todo descartado o correo sin imagenes", min_bytes, message_id)
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


def ensure_user_label_id(service: Any, label_name: str) -> Optional[str]:
    """
    Obtiene el id de una etiqueta de usuario por nombre exacto; la crea si no existe.
    """
    try:
        resp = service.users().labels().list(userId="me").execute()
        for lb in resp.get("labels", []):
            if lb.get("name") == label_name:
                return lb.get("id")
        created = service.users().labels().create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        return created.get("id")
    except Exception as e:
        logger.warning("ensure_user_label_id %s: %s", label_name, e)
        return None


def get_or_create_pagos_gmail_plantilla_label_ids(
    service: Any, cache: Optional[Dict[str, Optional[str]]] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Resuelve ids para MERCANTIL (A) / BNC (B) / BINANCE (C) / BNV (D) con cache opcional por nombre.
    """
    c = cache if cache is not None else {}
    k1, k2, k3, k4 = (
        PAGOS_GMAIL_LABEL_IMAGEN_1,
        PAGOS_GMAIL_LABEL_IMAGEN_2,
        PAGOS_GMAIL_LABEL_IMAGEN_3,
        PAGOS_GMAIL_LABEL_IMAGEN_4,
    )
    if k1 not in c:
        c[k1] = ensure_user_label_id(service, k1)
    if k2 not in c:
        c[k2] = ensure_user_label_id(service, k2)
    if k3 not in c:
        c[k3] = ensure_user_label_id(service, k3)
    if k4 not in c:
        c[k4] = ensure_user_label_id(service, k4)
    return c[k1], c[k2], c[k3], c[k4]


def add_message_star_and_user_labels(
    service: Any, message_id: str, user_label_ids: List[str]
) -> None:
    """Anade STARRED y las etiquetas de usuario indicadas (ids Gmail)."""
    add_ids = ["STARRED"] + [x for x in user_label_ids if x]
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": add_ids},
        ).execute()
    except Exception as e:
        logger.warning("add_message_star_and_user_labels %s: %s", message_id, e)


def add_message_user_labels_only(
    service: Any, message_id: str, user_label_ids: List[str]
) -> None:
    """Anade solo etiquetas de usuario (sin estrella). Ej. ERROR EMAIL o MANUAL."""
    add_ids = [x for x in user_label_ids if x]
    if not add_ids:
        return
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": add_ids},
        ).execute()
    except Exception as e:
        logger.warning("add_message_user_labels_only %s: %s", message_id, e)


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
    """Destaca el mensaje y lo deja como no leido (legacy; pipeline actual usa mark_starred_and_read / mark_unread_clear_star)."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["STARRED", "UNREAD"]},
        ).execute()
    except Exception as e:
        logger.warning("Error mark_starred_and_unread %s: %s", message_id, e)


def mark_starred_and_read(service: Any, message_id: str) -> None:
    """Estrella el mensaje y quita no leido: digitalizacion completa (A/B o C con fila en BD)."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["STARRED"], "removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception as e:
        logger.warning("Error mark_starred_and_read %s: %s", message_id, e)


def mark_unread_clear_star(service: Any, message_id: str) -> None:
    """Quita estrella y deja no leido: sin digitalizar o datos incompletos (reintento manual)."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": ["UNREAD"], "removeLabelIds": ["STARRED"]},
        ).execute()
    except Exception as e:
        logger.warning("Error mark_unread_clear_star %s: %s", message_id, e)
