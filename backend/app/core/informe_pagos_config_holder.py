"""
Holder de configuración para informe de pagos (Google Drive, Sheets, OCR, email).
Usado por: subida de imágenes a Drive, OCR, digitalización en Sheet, envío de email 6:00/13:00/16:30.
La config se guarda en tabla configuracion (clave informe_pagos_config).
"""
import json
import logging
import re
from typing import Any, List

logger = logging.getLogger(__name__)

CLAVE_INFORME_PAGOS_CONFIG = "informe_pagos_config"
_current: dict[str, Any] = {}

# Horarios envío (America/Caracas): 6:00, 13:00, 16:30
HORARIOS_ENVIO_DEFAULT = [{"hour": 6, "minute": 0}, {"hour": 13, "minute": 0}, {"hour": 16, "minute": 30}]


def sync_from_db() -> None:
    """Carga informe_pagos_config desde la tabla configuracion."""
    try:
        from app.core.database import SessionLocal
        from app.models.configuracion import Configuracion
        db = SessionLocal()
        try:
            row = db.get(Configuracion, CLAVE_INFORME_PAGOS_CONFIG)
            if not row or not row.valor:
                logger.info("[INFORME_PAGOS] sync_from_db: no hay fila o valor en BD (clave=%s); config vacía.", CLAVE_INFORME_PAGOS_CONFIG)
                _current.clear()
                return
            data = json.loads(row.valor)
            if not isinstance(data, dict):
                logger.warning("[INFORME_PAGOS] sync_from_db: valor en BD no es dict; config no actualizada.")
                return
            _current.clear()
            _current.update(data)
            has_json = bool((data.get("google_credentials_json") or "").strip())
            has_oauth = bool((data.get("google_oauth_refresh_token") or "").strip())
            logger.info(
                "[INFORME_PAGOS] sync_from_db OK: config cargada desde BD (cuenta_servicio=%s oauth=%s).",
                has_json, has_oauth,
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning("[INFORME_PAGOS] sync_from_db FALLO: no se pudo cargar informe_pagos_config: %s", e, exc_info=True)


def get_informe_pagos_config() -> dict[str, Any]:
    """Devuelve la config actual (Google Drive, Sheets, OCR, destinatarios, horarios)."""
    if not _current:
        sync_from_db()
    return dict(_current)


def get_google_drive_folder_id() -> str:
    """ID de la carpeta de Google Drive donde se suben las imágenes."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_drive_folder_id") or "").strip()


def get_google_credentials_json() -> str:
    """Contenido JSON de la cuenta de servicio (Drive + Sheets + Vision)."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_credentials_json") or "").strip()


def get_google_oauth_client_id() -> str:
    """Client ID del cliente OAuth (Drive/Sheets cuando no hay cuenta de servicio)."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_oauth_client_id") or "").strip()


def get_google_oauth_client_secret() -> str:
    """Client secret del cliente OAuth."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_oauth_client_secret") or "").strip()


def get_google_oauth_refresh_token() -> str:
    """Refresh token OAuth (obtenido tras autorizar una vez con Google)."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_oauth_refresh_token") or "").strip()


def use_google_oauth() -> bool:
    """True si debemos usar OAuth (refresh_token) en lugar de cuenta de servicio para Drive/Sheets."""
    return bool(get_google_oauth_refresh_token())


def get_google_sheets_id() -> str:
    """ID de la hoja de cálculo (desde la URL)."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_sheets_id") or "").strip()


def get_sheet_tab_principal() -> str:
    """
    Nombre de la pestaña donde escribir (ej. "Hoja 1").
    Si está vacío, se usan pestañas por periodo: 6am, 1pm, 4h30.
    Útil para que los datos aparezcan en la pestaña por defecto en lugar de en 6am/1pm/4h30.
    """
    cfg = get_informe_pagos_config()
    return (cfg.get("sheet_tab_principal") or "").strip()


def get_ocr_keywords_numero_documento() -> List[str]:
    """
    Palabras clave para ubicar 'Número de documento' en el texto OCR (sin formato estándar).
    Ej: "numero de documento", "numero de recibo", "nº doc". Si la línea contiene alguna, se extrae el valor (números, letras o mixto).
    Valor en config: string separado por comas o saltos de línea; o lista JSON. Si vacío, se usan las por defecto.
    """
    cfg = get_informe_pagos_config()
    raw = cfg.get("ocr_keywords_numero_documento")
    if raw is None or raw == "":
        return _default_keywords_numero_documento()
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return _default_keywords_numero_documento()
    # Aceptar separado por comas o por saltos de línea
    keywords = []
    for part in re.split(r"[\n,]+", s):
        k = part.strip()
        if k:
            keywords.append(k)
    return keywords if keywords else _default_keywords_numero_documento()


def _default_keywords_numero_documento() -> List[str]:
    """Palabras clave por defecto para ubicar número de documento en OCR."""
    return [
        "numero de documento",
        "numero de recibo",
        "número de documento",
        "número de recibo",
        "numero documento",
        "numero recibo",
        "nº documento",
        "nº recibo",
        "nº doc",
        "no. documento",
        "no. recibo",
        "documento n°",
        "recibo n°",
        "documento no",
        "recibo no",
    ]


def get_destinatarios_informe_emails() -> List[str]:
    """Emails que reciben el informe (6:00, 13:00, 16:30)."""
    cfg = get_informe_pagos_config()
    raw = cfg.get("destinatarios_informe_emails") or ""
    return [e.strip() for e in str(raw).split(",") if e.strip() and "@" in e.strip()]


def get_horarios_envio() -> List[dict]:
    """Lista de {hour, minute} para envío (default 6:00, 13:00, 16:30)."""
    cfg = get_informe_pagos_config()
    h = cfg.get("horarios_envio")
    if isinstance(h, list) and len(h) >= 1:
        return h
    return HORARIOS_ENVIO_DEFAULT


def update_from_api(data: dict[str, Any]) -> None:
    """Actualiza el holder desde la API de configuración."""
    for k, v in data.items():
        if v is not None:
            _current[k] = v
