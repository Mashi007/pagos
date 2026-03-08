"""
Credenciales para Gmail/Drive/Sheets del pipeline Pagos (cuenta corporativa).
Usa GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y archivo de tokens (GMAIL_TOKENS_PATH).
Si el proyecto usa informe_pagos_config_holder con OAuth, se pueden reutilizar esas credenciales
añadiendo los scopes de Gmail; aquí se intenta primero el token file del pipeline.
"""
import json
import logging
import os
from typing import Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES_GMAIL_DRIVE_SHEETS = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_pagos_gmail_credentials() -> Optional[Any]:
    """
    Obtiene credenciales para Gmail + Drive + Sheets.
    1) Si existe GMAIL_TOKENS_PATH con refresh_token, usa OAuth con settings GOOGLE_CLIENT_*.
    2) Si no, intenta get_google_credentials (informe_pagos) con scopes Gmail+Drive+Sheets.
    """
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    tokens_path = getattr(settings, "GMAIL_TOKENS_PATH", "gmail_tokens.json")
    if client_id and client_secret and tokens_path and os.path.isfile(tokens_path):
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                logger.warning("[PAGOS_GMAIL] No refresh_token en %s", tokens_path)
                return _fallback_informe_pagos_creds()
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials(
                token=data.get("token"),
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES_GMAIL_DRIVE_SHEETS,
            )
            creds.refresh(Request())
            with open(tokens_path, "w", encoding="utf-8") as f:
                json.dump({"refresh_token": refresh_token, "token": creds.token}, f, indent=2)
            return creds
        except Exception as e:
            logger.exception("[PAGOS_GMAIL] Error cargando/refrescando tokens: %s", e)
    return _fallback_informe_pagos_creds()


def _fallback_informe_pagos_creds() -> Optional[Any]:
    """Usa credenciales de informe pagos (OAuth o SA) si tienen los scopes necesarios."""
    try:
        from app.core.google_credentials import get_google_credentials
        return get_google_credentials(SCOPES_GMAIL_DRIVE_SHEETS)
    except Exception as e:
        logger.debug("[PAGOS_GMAIL] Fallback informe_pagos no disponible: %s", e)
    return None
