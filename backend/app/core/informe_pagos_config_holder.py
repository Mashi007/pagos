"""
Holder de configuración para informe de pagos (Google Drive, Sheets, OCR, email).
Usado por: subida de imágenes a Drive, OCR, digitalización en Sheet, envío de email 6:00/13:00/16:30.
La config se guarda en tabla configuracion (clave informe_pagos_config).
"""
import json
import logging
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
            if row and row.valor:
                data = json.loads(row.valor)
                if isinstance(data, dict):
                    _current.clear()
                    _current.update(data)
        finally:
            db.close()
    except Exception as e:
        logger.debug("No se pudo cargar informe_pagos_config: %s", e)


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


def get_google_sheets_id() -> str:
    """ID de la hoja de cálculo (desde la URL)."""
    cfg = get_informe_pagos_config()
    return (cfg.get("google_sheets_id") or "").strip()


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
