"""
Credenciales para Gmail/Drive/Sheets del pipeline Pagos (cuenta corporativa).
Usa GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y archivo de tokens (GMAIL_TOKENS_PATH).
Si el proyecto usa informe_pagos_config_holder con OAuth, se pueden reutilizar esas credenciales
añadiendo los scopes de Gmail; aquí se intenta primero el token file del pipeline.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

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


def get_pagos_gmail_credentials(
    *,
    tokens_path: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    allow_informe_fallback: bool = True,
) -> Optional[Any]:
    """
    Obtiene credenciales para Gmail + Drive + Sheets.
    1) Si existe tokens_path (o GMAIL_TOKENS_PATH) con refresh_token, usa OAuth con client id/secret.
    2) Si allow_informe_fallback y no hay archivo, intenta get_google_credentials (informe_pagos).
    """
    cid = (client_id if client_id is not None else getattr(settings, "GOOGLE_CLIENT_ID", None)) or None
    csec = (
        client_secret if client_secret is not None else getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    ) or None
    path = (
        tokens_path
        if tokens_path is not None
        else (getattr(settings, "GMAIL_TOKENS_PATH", "gmail_tokens.json") or "gmail_tokens.json")
    )
    if not cid or not csec:
        logger.debug(
            "%s No se usa archivo de tokens: GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET no configurados (env). Se intentará credenciales desde BD (Informe de pagos).",
            CONFIG_LOG_PREFIX,
        )
    elif not path or not os.path.isfile(path):
        logger.debug(
            "%s No se usa archivo de tokens: path vacío o archivo no existe (%s). Se intentará credenciales desde BD.",
            CONFIG_LOG_PREFIX, path or "(vacío)",
        )
    elif cid and csec and path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                logger.warning("%s Archivo %s no contiene refresh_token. Revisar contenido del archivo.", CONFIG_LOG_PREFIX, path)
                log_pagos_gmail_config_status()
                return _fallback_informe_pagos_creds() if allow_informe_fallback else None
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials(
                token=data.get("token"),
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=cid,
                client_secret=csec,
                scopes=SCOPES_GMAIL_DRIVE_SHEETS,
            )
            creds.refresh(Request())
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"refresh_token": refresh_token, "token": creds.token}, f, indent=2)
            return creds
        except Exception as e:
            logger.exception("[PAGOS_GMAIL] Error cargando/refrescando tokens (%s): %s", path, e)
            log_pagos_gmail_config_status()
    else:
        log_pagos_gmail_config_status()

    if not allow_informe_fallback:
        return None
    creds_fallback = _fallback_informe_pagos_creds()
    if creds_fallback is None:
        log_pagos_gmail_config_status()
    return creds_fallback


def _strip_oauth_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def get_cobranza_oauth_client_pair() -> Tuple[Optional[str], Optional[str]]:
    """
    Par OAuth para cobranza@ (Auditoría → Email).

    Solo AUDITORIA_EMAIL_GOOGLE_CLIENT_* — sin fallback a GOOGLE_* (itmaster) ni BD
    informe_pagos, para no mezclar client_id/redirect_uri ni cuentas Gmail.
    """
    audit_id = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_ID", None)
    )
    audit_sec = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET", None)
    )
    return audit_id, audit_sec


def cobranza_oauth_config_status() -> Dict[str, Any]:
    """Diagnóstico sin secretos: origen del client_id y si el par está completo."""
    audit_id = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_ID", None)
    )
    audit_sec = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET", None)
    )
    cid, csec = get_cobranza_oauth_client_pair()

    if audit_id and audit_sec:
        source = "auditoria_email_env"
    elif audit_id and not audit_sec:
        source = "misconfigured_audit_id_without_secret"
    elif not audit_id and not audit_sec:
        source = "missing_auditoria_email_env"
    else:
        source = "missing"

    suffix = None
    if cid:
        suffix = cid if len(cid) <= 24 else f"...{cid[-24:]}"

    secret_suffix = None
    secret_len = None
    if csec:
        secret_len = len(csec)
        secret_suffix = csec[-4:] if len(csec) >= 4 else csec

    google_sec = _strip_oauth_value(getattr(settings, "GOOGLE_CLIENT_SECRET", None))
    secrets_match_google_env: Optional[bool] = None
    if audit_sec and google_sec:
        secrets_match_google_env = audit_sec == google_sec

    return {
        "oauth_client_source": source,
        "oauth_client_id_suffix": suffix,
        "oauth_client_configured": bool(cid and csec),
        "oauth_client_secret_len": secret_len,
        "oauth_client_secret_suffix": secret_suffix,
        "oauth_secrets_match_google_env": secrets_match_google_env,
    }


def cobranza_oauth_log_context() -> str:
    """Fragmento seguro para logs (sin secret completo). Buscar [AUDITORIA_EMAIL] en Render."""
    st = cobranza_oauth_config_status()
    match = st.get("oauth_secrets_match_google_env")
    match_s = "n/a" if match is None else ("yes" if match else "NO")
    return (
        f"source={st.get('oauth_client_source')} "
        f"client={st.get('oauth_client_id_suffix')} "
        f"secret_len={st.get('oauth_client_secret_len')} "
        f"secret_suffix={st.get('oauth_client_secret_suffix')} "
        f"match_GOOGLE_CLIENT_SECRET={match_s}"
    )


def get_cobranza_gmail_credentials() -> Optional[Any]:
    """
    Credenciales del buzón cobranza@ (Auditoría → Email).
    Usa GMAIL_TOKENS_PATH_COBRANZA y get_cobranza_oauth_client_pair().
    No hace fallback a Informe de pagos (evita mezclar casillas).
    """
    path = (
        getattr(settings, "GMAIL_TOKENS_PATH_COBRANZA", None) or "gmail_tokens_cobranza.json"
    ).strip()
    cid, csec = get_cobranza_oauth_client_pair()
    return get_pagos_gmail_credentials(
        tokens_path=path,
        client_id=cid,
        client_secret=csec,
        allow_informe_fallback=False,
    )


def save_cobranza_gmail_tokens(*, refresh_token: str, access_token: Optional[str] = None) -> str:
    """Persiste tokens OAuth de cobranza@ en GMAIL_TOKENS_PATH_COBRANZA. Devuelve la ruta."""
    path = (
        getattr(settings, "GMAIL_TOKENS_PATH_COBRANZA", None) or "gmail_tokens_cobranza.json"
    ).strip()
    payload = {"refresh_token": refresh_token}
    if access_token:
        payload["token"] = access_token
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("%s Tokens cobranza@ guardados en %s", CONFIG_LOG_PREFIX, path)
    return path


def pagos_gmail_credentials_configured() -> bool:
    """
    Comprueba que hay material OAuth/SA para Gmail sin llamar a Google (respuesta HTTP rápida).
    El pipeline en background llama a get_pagos_gmail_credentials() y refresca el token allí.
    """
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    tokens_path = getattr(settings, "GMAIL_TOKENS_PATH", "gmail_tokens.json") or "gmail_tokens.json"
    if client_id and client_secret and tokens_path and os.path.isfile(tokens_path):
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("refresh_token"):
                return True
        except Exception:
            pass
    try:
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
            cid = get_google_oauth_client_id()
            csec = get_google_oauth_client_secret()
            ref = get_google_oauth_refresh_token()
            return bool(
                (cid or "").strip()
                and (csec or "").strip()
                and (ref or "").strip()
            )
        sa_json = get_google_credentials_json()
        return bool((sa_json or "").strip())
    except Exception:
        return False


def _fallback_informe_pagos_creds() -> Optional[Any]:
    """
    Usa credenciales de informe pagos (OAuth o SA) si tienen los scopes necesarios.
    Usa SCOPES_INFORME_PAGOS_GMAIL (drive.file, no drive completo) para no provocar
    invalid_scope al refrescar el token emitido por «Conectar con Google».
    """
    try:
        from app.core.google_credentials import get_google_credentials
        creds = get_google_credentials(SCOPES_INFORME_PAGOS_GMAIL)
        if creds is not None:
            logger.info("%s Usando credenciales desde Configuración > Informe de pagos (BD).", CONFIG_LOG_PREFIX)
        return creds
    except Exception as e:
        logger.debug("[PAGOS_GMAIL] Fallback informe_pagos no disponible: %s", e)
    return None
