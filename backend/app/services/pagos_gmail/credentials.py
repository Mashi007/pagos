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

# Prefijo para que en logs sea fácil buscar qué está mal configurado
CONFIG_LOG_PREFIX = "[PAGOS_GMAIL_CONFIG]"


def log_pagos_gmail_config_status() -> None:
    """
    Escribe en log el estado de la configuración (sin valores sensibles) para diagnosticar
    por qué falla el pipeline. Buscar en logs "[PAGOS_GMAIL_CONFIG]" para ver qué falta.
    """
    items = []
    # Env / settings (pipeline directo)
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    tokens_path = getattr(settings, "GMAIL_TOKENS_PATH", "gmail_tokens.json") or "gmail_tokens.json"
    has_file = os.path.isfile(tokens_path)
    items.append(f"GOOGLE_CLIENT_ID={('OK' if (client_id and client_id.strip()) else 'NO CONFIGURADO')}")
    items.append(f"GOOGLE_CLIENT_SECRET={('OK' if (client_secret and client_secret.strip()) else 'NO CONFIGURADO')}")
    items.append(f"GMAIL_TOKENS_PATH={tokens_path} (archivo {'existe' if has_file else 'NO EXISTE'})")
    if has_file:
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            has_refresh = bool(data.get("refresh_token"))
            items.append(f"refresh_token en archivo={'OK' if has_refresh else 'NO'}")
        except Exception as e:
            items.append(f"lectura archivo tokens: error ({e})")
    # Fallback: informe_pagos (BD)
    try:
        from app.core.informe_pagos_config_holder import (
            get_google_oauth_client_id,
            get_google_oauth_client_secret,
            get_google_oauth_refresh_token,
            sync_from_db,
        )
        sync_from_db()
        cid = get_google_oauth_client_id()
        csec = get_google_oauth_client_secret()
        ref = get_google_oauth_refresh_token()
        items.append(
            f"informe_pagos (BD): client_id={'OK' if (cid and cid.strip()) else 'NO'}, "
            f"client_secret={'OK' if (csec and csec.strip()) else 'NO'}, "
            f"refresh_token={'OK' if (ref and ref.strip()) else 'NO'}"
        )
    except Exception as e:
        items.append(f"informe_pagos (BD): no disponible ({e})")
    # Gemini (necesario para extraer datos de comprobantes)
    gemini_key = getattr(settings, "GEMINI_API_KEY", None)
    items.append(f"GEMINI_API_KEY={('OK' if (gemini_key and gemini_key.strip()) else 'NO CONFIGURADO')}")
    logger.warning("%s Estado: %s", CONFIG_LOG_PREFIX, " | ".join(items))


# Scopes para pipeline con archivo de tokens (pueden incluir drive completo)
SCOPES_GMAIL_DRIVE_SHEETS = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Scopes que coincide con el token de Configuración > Google (informe de pagos).
# Ese token se emite con drive.file (no drive completo); pedir "drive" en refresh da invalid_scope.
SCOPES_INFORME_PAGOS_GMAIL = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
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
    if not client_id or not client_secret:
        logger.warning(
            "%s No se usa archivo de tokens: GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET no configurados (env).",
            CONFIG_LOG_PREFIX,
        )
    elif not tokens_path or not os.path.isfile(tokens_path):
        logger.warning(
            "%s No se usa archivo de tokens: GMAIL_TOKENS_PATH vacío o archivo no existe (%s).",
            CONFIG_LOG_PREFIX, tokens_path or "(vacío)",
        )
    elif client_id and client_secret and tokens_path and os.path.isfile(tokens_path):
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                logger.warning("%s Archivo %s no contiene refresh_token. Revisar contenido del archivo.", CONFIG_LOG_PREFIX, tokens_path)
                log_pagos_gmail_config_status()
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
            log_pagos_gmail_config_status()
    else:
        log_pagos_gmail_config_status()

    creds_fallback = _fallback_informe_pagos_creds()
    if creds_fallback is None:
        log_pagos_gmail_config_status()
    return creds_fallback


def _fallback_informe_pagos_creds() -> Optional[Any]:
    """
    Usa credenciales de informe pagos (OAuth o SA) si tienen los scopes necesarios.
    Usa SCOPES_INFORME_PAGOS_GMAIL (drive.file, no drive completo) para no provocar
    invalid_scope al refrescar el token emitido por «Conectar con Google».
    """
    try:
        from app.core.google_credentials import get_google_credentials
        return get_google_credentials(SCOPES_INFORME_PAGOS_GMAIL)
    except Exception as e:
        logger.debug("[PAGOS_GMAIL] Fallback informe_pagos no disponible: %s", e)
    return None
