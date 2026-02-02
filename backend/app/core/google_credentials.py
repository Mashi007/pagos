"""
Credenciales Google para Drive, Sheets y Vision (OCR).
Devuelve credenciales de cuenta de servicio (SA) o OAuth según la configuración de informe pagos.
"""
import json
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def get_google_credentials(scopes: List[str]) -> Optional[Any]:
    """
    Devuelve credenciales válidas para las APIs de Google con los scopes indicados.
    - Si hay refresh_token OAuth configurado: usa OAuth (client_id, client_secret, refresh_token).
    - Si no: usa cuenta de servicio (google_credentials_json).
    Devuelve None si no hay credenciales configuradas o falla el refresh.
    """
    from app.core.informe_pagos_config_holder import (
        get_google_credentials_json,
        get_google_oauth_client_id,
        get_google_oauth_client_secret,
        get_google_oauth_refresh_token,
        sync_from_db,
        use_google_oauth,
    )
    sync_from_db()

    if use_google_oauth():
        return _credentials_oauth(scopes)
    return _credentials_service_account(scopes)


def _credentials_oauth(scopes: List[str]) -> Optional[Any]:
    """Credenciales desde refresh_token (OAuth)."""
    from app.core.informe_pagos_config_holder import (
        get_google_oauth_client_id,
        get_google_oauth_client_secret,
        get_google_oauth_refresh_token,
    )
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    client_id = get_google_oauth_client_id()
    client_secret = get_google_oauth_client_secret()
    refresh_token = get_google_oauth_refresh_token()
    if not client_id or not client_secret or not refresh_token:
        logger.warning("OAuth configurado pero faltan client_id, client_secret o refresh_token.")
        return None
    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        creds.refresh(Request())
        return creds
    except Exception as e:
        logger.exception("Error refrescando credenciales OAuth: %s", e)
        return None


def _credentials_service_account(scopes: List[str]) -> Optional[Any]:
    """Credenciales desde JSON de cuenta de servicio."""
    from app.core.informe_pagos_config_holder import get_google_credentials_json
    from google.oauth2 import service_account

    creds_json = get_google_credentials_json()
    if not creds_json:
        return None
    try:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    except Exception as e:
        logger.exception("Error cargando credenciales de cuenta de servicio: %s", e)
        return None
