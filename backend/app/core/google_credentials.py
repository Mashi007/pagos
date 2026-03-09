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
        logger.info("[INFORME_PAGOS] get_google_credentials: usando OAuth (refresh_token)")
        return _credentials_oauth(scopes)
    logger.info("[INFORME_PAGOS] get_google_credentials: usando cuenta de servicio (JSON)")
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
        missing = [k for k, v in [("google_oauth_client_id", client_id), ("google_oauth_client_secret", client_secret), ("google_oauth_refresh_token", refresh_token)] if not (v and str(v).strip())]
        logger.warning(
            "[INFORME_PAGOS] [CONFIG] OAuth no puede usarse: faltan en BD (informe_pagos_config): %s. "
            "Configure estos campos en Configuración > Informe de pagos o bien use GOOGLE_CLIENT_ID/SECRET y GMAIL_TOKENS_PATH por env.",
            ", ".join(missing) or "client_id, client_secret o refresh_token",
        )
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
        logger.info("[INFORME_PAGOS] OAuth: credenciales refrescadas OK.")
        return creds
    except Exception as e:
        err_str = str(e).lower()
        logger.exception("[INFORME_PAGOS] OAuth FALLO: error refrescando credenciales: %s", e)
        if "invalid_client" in err_str or "unauthorized" in err_str:
            logger.warning(
                "[CONFIG] Google devolvió 'invalid_client'/'Unauthorized'. "
                "En este momento se usan las credenciales de la BD (informe_pagos_config), no las variables de entorno: "
                "actualice 'Client ID' y 'Client secret' en la app (Configuración > Informe de pagos) para que coincidan exactamente con Google Cloud Console > APIs y servicios > Credenciales > OAuth 2.0. "
                "Si regeneró el Client Secret en la consola, péguelo de nuevo en la configuración."
            )
        elif "invalid_scope" in err_str:
            logger.warning(
                "[CONFIG] Google devolvió 'invalid_scope'. El refresh_token actual no tiene los permisos (scopes) que pide la app (p. ej. Gmail o Vision). "
                "Solución: en Configuración > Google (Drive, Sheets, Gmail, OCR) pulse «Conectar con Google» de nuevo y autorice todos los accesos."
            )
        elif "reauthentication" in err_str or "reauth" in err_str:
            logger.warning(
                "[CONFIG] Google pide reautenticación. En Configuración > Google (Drive, Sheets, Gmail, OCR) pulse «Conectar con Google» de nuevo y vuelva a autorizar."
            )
        elif "invalid_grant" in err_str or "expired" in err_str or "revoked" in err_str:
            logger.warning(
                "[CONFIG] Token OAuth expirado o revocado. En Configuración > Google (Drive, Sheets, Gmail, OCR) pulse «Conectar con Google» y complete la autorización para obtener un nuevo token."
            )
        return None


def _is_service_account_info(creds_dict: dict) -> bool:
    """Comprueba si el dict tiene el formato de cuenta de servicio (no OAuth client)."""
    return bool(
        isinstance(creds_dict, dict)
        and creds_dict.get("client_email")
        and (creds_dict.get("token_uri") or creds_dict.get("private_key"))
    )


def _credentials_service_account(scopes: List[str]) -> Optional[Any]:
    """Credenciales desde JSON de cuenta de servicio."""
    from app.core.informe_pagos_config_holder import get_google_credentials_json
    from google.oauth2 import service_account

    creds_json = get_google_credentials_json()
    if not creds_json:
        logger.warning("[INFORME_PAGOS] Cuenta de servicio: google_credentials_json vacío o no configurado.")
        return None
    try:
        creds_dict = json.loads(creds_json)
        if not _is_service_account_info(creds_dict):
            logger.warning(
                "[INFORME_PAGOS] El JSON de 'Credenciales Google' no es de cuenta de servicio (falta client_email/token_uri). "
                "Si usas OAuth, deja este campo vacío y usa 'Conectar con Google (OAuth)'."
            )
            return None
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        logger.info("[INFORME_PAGOS] Cuenta de servicio: credenciales cargadas OK (client_email=%s).", creds_dict.get("client_email", "?"))
        return creds
    except json.JSONDecodeError as e:
        logger.exception("[INFORME_PAGOS] Cuenta de servicio FALLO: JSON inválido: %s", e)
        return None
    except Exception as e:
        logger.exception("[INFORME_PAGOS] Cuenta de servicio FALLO: %s", e)
        return None
