# -*- coding: utf-8 -*-
"""
Migración operativa: enlaces de comprobante en Google Drive → tabla ``pago_comprobante_imagen``
y ``pagos.link_comprobante`` apuntando al GET interno (misma convención que pipeline Gmail).

No altera el esquema de BD. Ejecutar desde ``scripts/migrar_comprobantes_drive_a_bd.py``.
"""
from __future__ import annotations

import io
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

_RE_FILE_D = re.compile(r"/file/d/([a-zA-Z0-9_-]+)", re.IGNORECASE)
_RE_OPEN_ID = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)", re.IGNORECASE)
_RAW_ID = re.compile(r"^[a-zA-Z0-9_-]{25,}$")

# Google Docs/Sheets no son binarios descargables con get_media sin export
_GOOGLE_APPS_PREFIX = "application/vnd.google-apps."


def extraer_google_drive_file_id(texto: str) -> Optional[str]:
    """
    Obtiene el file id de URLs típicas de Drive o cadena que ya es solo el id.
    Devuelve None si no aplica o si es URL de comprobante interno.
    """
    s = (texto or "").strip()
    if not s or "comprobante-imagen" in s.lower():
        return None
    m = _RE_FILE_D.search(s)
    if m:
        return m.group(1)
    m = _RE_OPEN_ID.search(s)
    if m and len(m.group(1)) >= 10:
        return m.group(1)
    if _RAW_ID.match(s) and not s.isdigit():
        return s
    return None


def enlace_requiere_migracion_drive_a_bd(link: Optional[str]) -> bool:
    """True si el link parece Drive (o id suelto) y aún no es comprobante en BD vía API."""
    s = (link or "").strip()
    if not s:
        return False
    low = s.lower()
    if "comprobante-imagen" in low:
        return False
    if "drive.google.com" in low:
        return extraer_google_drive_file_id(s) is not None
    return extraer_google_drive_file_id(s) is not None


def _credenciales_drive_descarga() -> Tuple[Optional[Any], str]:
    """
    Intenta credenciales con acceso a archivos Drive (misma cuenta que sube comprobantes Gmail).
    Retorna (creds, origen) donde origen es etiqueta de log.
    """
    try:
        from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials

        c = get_pagos_gmail_credentials()
        if c is not None:
            return c, "pagos_gmail_tokens"
    except Exception as e:
        logger.debug("[MIG_DRIVE_BD] get_pagos_gmail_credentials: %s", e)
    try:
        from app.core.google_credentials import get_google_credentials

        for scopes in (
            ("https://www.googleapis.com/auth/drive.readonly",),
            ("https://www.googleapis.com/auth/drive",),
            (
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive.readonly",
            ),
        ):
            c = get_google_credentials(list(scopes))
            if c is not None:
                return c, f"informe_google_scopes={scopes}"
    except Exception as e:
        logger.debug("[MIG_DRIVE_BD] get_google_credentials: %s", e)
    return None, "ninguna"


def descargar_archivo_drive_con_api(file_id: str) -> Tuple[Optional[bytes], Optional[str], Optional[str], str]:
    """
    Descarga contenido con Drive API v3 (get + get_media).

    Retorna (body, mime_declarado, nombre_archivo, mensaje_error).
    mensaje_error vacío si OK.
    """
    creds, _orig = _credenciales_drive_descarga()
    if creds is None:
        return None, None, None, "sin_credenciales_google"
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = (
            service.files()
            .get(fileId=file_id, fields="mimeType,name,size", supportsAllDrives=True)
            .execute()
        )
        mime = (meta.get("mimeType") or "").strip()
        name = (meta.get("name") or "").strip() or f"drive_{file_id}"
        if mime.startswith(_GOOGLE_APPS_PREFIX):
            return None, mime, name, f"google_workspace:{mime}"
        fh = io.BytesIO()
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        body = fh.getvalue()
        if not body:
            return None, mime, name, "archivo_vacio"
        return body, mime or None, name, ""
    except Exception as e:
        logger.warning("[MIG_DRIVE_BD] API file_id=%s… error=%s", file_id[:8], e)
        return None, None, None, f"api_error:{e!s}"[:500]


def _parse_confirm_token_from_html(html: bytes) -> Optional[str]:
    try:
        t = html.decode("utf-8", errors="ignore")
    except Exception:
        return None
    m = re.search(r"confirm=([0-9A-Za-z_-]+)", t)
    if m:
        return m.group(1)
    m2 = re.search(r"uuid=([0-9A-Za-z_-]+)", t)
    if m2:
        return m2.group(1)
    return None


def descargar_archivo_drive_uc_export(file_id: str) -> Tuple[Optional[bytes], Optional[str], str]:
    """
    Descarga anónima vía ``uc?export=download`` (archivos «cualquiera con el enlace»).
    No sustituye la API si el archivo es privado.
    """
    base = f"https://drive.google.com/uc?export=download&id={urllib.parse.quote(file_id)}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RapiCredit-migracion-comprobante/1.0)"}
    try:
        req = urllib.request.Request(base, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosec B310 — URL fija Drive
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    except urllib.error.HTTPError as e:
        return None, None, f"uc_http:{e.code}"
    except Exception as e:
        return None, None, f"uc_error:{e!s}"[:300]

    if len(data) < 500000 and b"virus scan" in data.lower()[:8000]:
        tok = _parse_confirm_token_from_html(data)
        if tok:
            url2 = f"https://drive.google.com/uc?export=download&id={urllib.parse.quote(file_id)}&confirm={urllib.parse.quote(tok)}"
            try:
                req2 = urllib.request.Request(url2, headers=headers, method="GET")
                with urllib.request.urlopen(req2, timeout=120) as resp2:  # nosec B310
                    data = resp2.read()
                    ctype = (resp2.headers.get("Content-Type") or "").split(";")[0].strip()
            except Exception as e:
                return None, None, f"uc_confirm_error:{e!s}"[:300]

    if len(data) < 2000 and (b"<html" in data[:500].lower() or b"<!doctype" in data[:500].lower()):
        return None, None, "uc_respuesta_html_no_binario"

    return data, ctype or None, ""


def normalizar_mime_comprobante(
    body: bytes,
    mime_api: Optional[str],
    nombre_hint: str,
) -> Optional[str]:
    """Alineado con alta manual: MIME permitido + magic bytes."""
    from app.services.cobros.cobros_publico_reporte_service import (
        ALLOWED_COMPROBANTE_TYPES,
        mime_efectivo_comprobante_web,
        validate_file_magic,
    )

    cand = mime_efectivo_comprobante_web(mime_api or "", nombre_hint)
    base_allowed = {x.split(";")[0].strip().lower() for x in ALLOWED_COMPROBANTE_TYPES}
    if cand.lower() in base_allowed and validate_file_magic(body, cand):
        if cand.lower() == "image/jpg":
            return "image/jpeg"
        return cand
    for try_ct in (
        "image/jpeg",
        "image/png",
        "application/pdf",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
    ):
        if validate_file_magic(body, try_ct):
            return try_ct
    return None


def descargar_y_normalizar_comprobante_drive(file_id: str) -> Tuple[Optional[bytes], Optional[str], str]:
    """
    Intenta API y luego uc=export. Retorna (bytes, mime_normalizado, error).
    """
    body, mime_meta, _name, err_api = descargar_archivo_drive_con_api(file_id)
    nombre = _name or "comprobante"
    if body and not err_api:
        mime_ok = normalizar_mime_comprobante(body, mime_meta, nombre)
        if mime_ok:
            return body, mime_ok, ""
        return None, None, f"mime_no_admitido_o_magic:{mime_meta}"

    body2, ctype_uc, err_uc = descargar_archivo_drive_uc_export(file_id)
    if err_uc and not body2:
        detalle = err_api or err_uc
        return None, None, detalle
    if not body2:
        return None, None, err_api or err_uc or "sin_datos"
    mime_ok = normalizar_mime_comprobante(body2, ctype_uc, nombre)
    if mime_ok:
        return body2, mime_ok, ""
    return None, None, f"uc_mime_no_admitido:{ctype_uc}"
