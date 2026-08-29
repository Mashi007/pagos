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

CLAVE_COBRANZA_GMAIL_TOKENS = "auditoria_email_gmail_tokens"
CONFIG_LOG_PREFIX = "[PAGOS_GMAIL_CONFIG]"


def _cobranza_tokens_path_resolved() -> str:
    return (
        getattr(settings, "GMAIL_TOKENS_PATH_COBRANZA", None) or "gmail_tokens_cobranza.json"
    ).strip()


def _load_cobranza_tokens_from_db(db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Tokens OAuth cobranza@ en PostgreSQL (sobrevive FS efímero de Render)."""
    try:
        from app.models.configuracion import Configuracion

        if db is not None:
            row = db.get(Configuracion, CLAVE_COBRANZA_GMAIL_TOKENS)
            if row and row.valor:
                data = json.loads(row.valor)
                return data if isinstance(data, dict) else None
            return None
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            row = session.get(Configuracion, CLAVE_COBRANZA_GMAIL_TOKENS)
            if row and row.valor:
                data = json.loads(row.valor)
                return data if isinstance(data, dict) else None
        finally:
            session.close()
    except Exception as e:
        logger.warning("%s No se pudo leer tokens cobranza@ de BD: %s", CONFIG_LOG_PREFIX, e)
    return None


def _save_cobranza_tokens_to_db(payload: Dict[str, Any], db: Optional[Any] = None) -> bool:
    try:
        from app.models.configuracion import Configuracion

        valor = json.dumps(payload)
        if db is not None:
            row = db.get(Configuracion, CLAVE_COBRANZA_GMAIL_TOKENS)
            if row:
                row.valor = valor
            else:
                db.add(Configuracion(clave=CLAVE_COBRANZA_GMAIL_TOKENS, valor=valor))
            db.commit()
            return True
        from app.core.database import SessionLocal

        session = SessionLocal()
        try:
            row = session.get(Configuracion, CLAVE_COBRANZA_GMAIL_TOKENS)
            if row:
                row.valor = valor
            else:
                session.add(Configuracion(clave=CLAVE_COBRANZA_GMAIL_TOKENS, valor=valor))
            session.commit()
            return True
        finally:
            session.close()
    except Exception as e:
        logger.exception("%s No se pudo guardar tokens cobranza@ en BD: %s", CONFIG_LOG_PREFIX, e)
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        return False


def load_cobranza_gmail_token_payload() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Carga refresh/access token de cobranza@.
    Returns (payload, source) con source en file | bd | none.
    """
    path = _cobranza_tokens_path_resolved()
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("refresh_token"):
                return data, "file"
        except Exception as e:
            logger.debug("%s Lectura tokens archivo %s: %s", CONFIG_LOG_PREFIX, path, e)
    data = _load_cobranza_tokens_from_db()
    if isinstance(data, dict) and data.get("refresh_token"):
        return data, "bd"
    return None, "none"


def cobranza_tokens_ready() -> bool:
    payload, _ = load_cobranza_gmail_token_payload()
    return bool(payload and payload.get("refresh_token"))


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

            def _creds_from_secret(secret: str) -> Any:
                c = Credentials(
                    token=data.get("token"),
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=cid,
                    client_secret=secret,
                    scopes=SCOPES_GMAIL_DRIVE_SHEETS,
                )
                c.refresh(Request())
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"refresh_token": refresh_token, "token": c.token}, f, indent=2)
                return c

            try:
                return _creds_from_secret(csec)
            except Exception as e:
                err = str(e).lower()
                ip_id, ip_sec = _informe_pagos_oauth_pair()
                if (
                    "invalid_client" in err
                    and ip_id
                    and ip_sec
                    and cid == ip_id
                    and ip_sec != csec
                ):
                    logger.info(
                        "%s Refresh con secret env falló (invalid_client); "
                        "reintentando con secret Informe pagos (BD) para mismo client_id.",
                        CONFIG_LOG_PREFIX,
                    )
                    return _creds_from_secret(ip_sec)
                raise
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


def _informe_pagos_oauth_pair() -> Tuple[Optional[str], Optional[str]]:
    """Client ID/secret OAuth guardados en BD (Configuración > Informe de pagos)."""
    try:
        from app.core.informe_pagos_config_holder import (
            get_google_oauth_client_id,
            get_google_oauth_client_secret,
            sync_from_db,
        )

        sync_from_db()
        return (
            _strip_oauth_value(get_google_oauth_client_id()),
            _strip_oauth_value(get_google_oauth_client_secret()),
        )
    except Exception:
        return None, None


def resolve_cobranza_oauth_client_pair() -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    """
    Par OAuth para cobranza@ (Auditoría → Email).

    Opción A (cliente Web compartido cobranzas / …bitt…):
    - Client ID: AUDITORIA_EMAIL_GOOGLE_CLIENT_ID en Render, o el de Informe de pagos (BD).
    - Client secret: si el ID coincide con Informe de pagos, usa el secret de BD
      (autoritativo tras «Guardar configuración»). Render AUDITORIA_EMAIL_* secret
      solo aplica si no hay par equivalente en BD.
    """
    audit_id = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_ID", None)
    )
    audit_sec_env = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET", None)
    )
    ip_id, ip_sec = _informe_pagos_oauth_pair()

    client_id = audit_id or ip_id
    if audit_id:
        id_source = "auditoria_email_env"
    elif ip_id:
        id_source = "informe_pagos_bd"
    else:
        id_source = "missing"

    if not client_id:
        return None, None, {
            "client_id_source": "missing",
            "client_secret_source": "missing",
        }

    client_secret: Optional[str] = None
    secret_source = "missing"

    shared_informe = bool(ip_id and client_id == ip_id and ip_sec)
    if shared_informe:
        client_secret = ip_sec
        secret_source = "informe_pagos_bd"
        if audit_sec_env and audit_sec_env != ip_sec:
            logger.info(
                "%s cobranza@ OAuth: secret Render (…%s) difiere de Informe pagos BD (…%s); "
                "usando BD para cliente compartido.",
                CONFIG_LOG_PREFIX,
                audit_sec_env[-4:] if len(audit_sec_env) >= 4 else "?",
                ip_sec[-4:] if len(ip_sec) >= 4 else "?",
            )
    elif audit_sec_env:
        client_secret = audit_sec_env
        secret_source = "auditoria_email_env"

    return client_id, client_secret, {
        "client_id_source": id_source,
        "client_secret_source": secret_source,
    }


def get_cobranza_oauth_client_pair() -> Tuple[Optional[str], Optional[str]]:
    """Par OAuth efectivo para cobranza@ (ver resolve_cobranza_oauth_client_pair)."""
    cid, csec, _ = resolve_cobranza_oauth_client_pair()
    return cid, csec


def _oauth_id_suffix(client_id: Optional[str]) -> Optional[str]:
    if not client_id:
        return None
    return client_id if len(client_id) <= 24 else f"...{client_id[-24:]}"


def _oauth_secret_fingerprint(client_secret: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    if not client_secret:
        return None, None
    return len(client_secret), (
        client_secret[-4:] if len(client_secret) >= 4 else client_secret
    )


def _informe_pagos_oauth_fingerprints() -> Dict[str, Any]:
    """Huellas del OAuth guardado en BD (Configuración > Informe de pagos). Sin secretos completos."""
    ip_id, ip_sec = _informe_pagos_oauth_pair()
    if not ip_id and not ip_sec:
        return {
            "informe_pagos_oauth_configured": False,
            "informe_pagos_oauth_client_id_suffix": None,
            "informe_pagos_oauth_secret_len": None,
            "informe_pagos_oauth_secret_suffix": None,
        }
    secret_len, secret_suffix = _oauth_secret_fingerprint(ip_sec)
    return {
        "informe_pagos_oauth_configured": bool(ip_id and ip_sec),
        "informe_pagos_oauth_client_id_suffix": _oauth_id_suffix(ip_id),
        "informe_pagos_oauth_secret_len": secret_len,
        "informe_pagos_oauth_secret_suffix": secret_suffix,
        "_ip_id": ip_id,
        "_ip_sec": ip_sec,
    }


def cobranza_oauth_config_status() -> Dict[str, Any]:
    """Diagnóstico sin secretos: origen del client_id/secret efectivos."""
    audit_id = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_ID", None)
    )
    audit_sec_env = _strip_oauth_value(
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET", None)
    )
    cid, csec, resolution = resolve_cobranza_oauth_client_pair()
    id_source = resolution.get("client_id_source") or "missing"
    secret_source = resolution.get("client_secret_source") or "missing"

    if cid and csec:
        if secret_source == "informe_pagos_bd":
            source = "shared_client_informe_pagos_bd"
        elif id_source == "auditoria_email_env" and secret_source == "auditoria_email_env":
            source = "auditoria_email_env"
        else:
            source = "configured"
    elif cid and not csec:
        source = "misconfigured_client_without_secret"
    else:
        source = "missing_auditoria_and_informe_oauth"

    secret_len, secret_suffix = _oauth_secret_fingerprint(csec)

    google_id = _strip_oauth_value(getattr(settings, "GOOGLE_CLIENT_ID", None))
    google_sec = _strip_oauth_value(getattr(settings, "GOOGLE_CLIENT_SECRET", None))
    secrets_match_google_env: Optional[bool] = None
    if audit_sec_env and google_sec:
        secrets_match_google_env = audit_sec_env == google_sec

    client_ids_match_google_env: Optional[bool] = None
    if audit_id and google_id:
        client_ids_match_google_env = audit_id == google_id

    ip = _informe_pagos_oauth_fingerprints()
    ip_id = ip.pop("_ip_id", None)
    ip_sec = ip.pop("_ip_sec", None)
    informe_secret_matches_auditoria_env: Optional[bool] = None
    informe_client_id_matches_auditoria: Optional[bool] = None
    if audit_sec_env and ip_sec:
        informe_secret_matches_auditoria_env = audit_sec_env == ip_sec
    if audit_id and ip_id:
        informe_client_id_matches_auditoria_env = audit_id == ip_id

    env_secret_len, env_secret_suffix = _oauth_secret_fingerprint(audit_sec_env)

    return {
        "oauth_client_source": source,
        "oauth_client_id_source": id_source,
        "oauth_client_secret_source": secret_source,
        "oauth_client_id_suffix": _oauth_id_suffix(cid),
        "oauth_client_configured": bool(cid and csec),
        "oauth_client_secret_len": secret_len,
        "oauth_client_secret_suffix": secret_suffix,
        "oauth_env_secret_suffix": env_secret_suffix,
        "oauth_env_secret_len": env_secret_len,
        "oauth_secrets_match_google_env": secrets_match_google_env,
        "oauth_client_ids_match_google_env": client_ids_match_google_env,
        "informe_pagos_oauth_secret_matches_auditoria_env": informe_secret_matches_auditoria_env,
        "informe_pagos_oauth_client_id_matches_auditoria_env": informe_client_id_matches_auditoria_env,
        **ip,
    }


def cobranza_oauth_log_context() -> str:
    """Fragmento seguro para logs (sin secret completo). Buscar [AUDITORIA_EMAIL] en Render."""
    st = cobranza_oauth_config_status()
    match = st.get("oauth_secrets_match_google_env")
    match_s = "n/a" if match is None else ("yes" if match else "NO")
    return (
        f"source={st.get('oauth_client_source')} "
        f"id_from={st.get('oauth_client_id_source')} "
        f"secret_from={st.get('oauth_client_secret_source')} "
        f"client={st.get('oauth_client_id_suffix')} "
        f"secret_len={st.get('oauth_client_secret_len')} "
        f"secret_suffix={st.get('oauth_client_secret_suffix')} "
        f"env_secret_suffix={st.get('oauth_env_secret_suffix')} "
        f"match_GOOGLE_CLIENT_SECRET={match_s}"
    )


def get_cobranza_gmail_credentials() -> Optional[Any]:
    """
    Credenciales del buzón cobranza@ (Auditoría → Email).
    Tokens desde archivo o BD (Render sin disco persistente).
    """
    payload, _ = load_cobranza_gmail_token_payload()
    if not payload or not payload.get("refresh_token"):
        return None
    cid, csec = get_cobranza_oauth_client_pair()
    if not cid or not csec:
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials(
            token=payload.get("token"),
            refresh_token=payload["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cid,
            client_secret=csec,
            scopes=SCOPES_GMAIL_DRIVE_SHEETS,
        )
        creds.refresh(Request())
        if creds.token and creds.token != payload.get("token"):
            save_cobranza_gmail_tokens(
                refresh_token=payload["refresh_token"],
                access_token=creds.token,
            )
        return creds
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Error credenciales cobranza@: %s", e)
        return None


def save_cobranza_gmail_tokens(
    *,
    refresh_token: str,
    access_token: Optional[str] = None,
    db: Optional[Any] = None,
) -> str:
    """
    Persiste tokens OAuth de cobranza@ en BD (primario) y archivo (espejo si es posible).
    En Render sin disco en /var/data, BD evita save_failed tras OAuth.
    """
    payload: Dict[str, Any] = {"refresh_token": refresh_token}
    if access_token:
        payload["token"] = access_token

    saved_bd = _save_cobranza_tokens_to_db(payload, db=db)
    path = _cobranza_tokens_path_resolved()
    saved_file = False
    # En Render sin disco writable, no spamear Permission denied en cada refresh.
    skip_file = os.environ.get("GMAIL_COBRANZA_SKIP_FILE_TOKENS", "").strip() in (
        "1",
        "true",
        "True",
        "yes",
    )
    if not skip_file and path.startswith("/var/data"):
        # Disco típico no montado / sin permisos en free web — BD alcanza.
        skip_file = True
    try:
        if skip_file:
            raise PermissionError(f"skip file tokens path={path}")
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        saved_file = True
        logger.info("%s Tokens cobranza@ guardados en %s", CONFIG_LOG_PREFIX, path)
    except PermissionError:
        if not getattr(save_cobranza_gmail_tokens, "_warned_skip_file", False):
            logger.info(
                "%s Tokens cobranza@ solo en BD (sin escribir %s)",
                CONFIG_LOG_PREFIX,
                path,
            )
            setattr(save_cobranza_gmail_tokens, "_warned_skip_file", True)
    except Exception as e:
        logger.warning(
            "%s No se pudo escribir tokens cobranza@ en %s (%s); BD=%s",
            CONFIG_LOG_PREFIX,
            path,
            e,
            "OK" if saved_bd else "NO",
        )

    if not saved_bd and not saved_file:
        raise OSError(
            f"No se pudo persistir tokens cobranza@ (archivo {path} ni BD "
            f"{CLAVE_COBRANZA_GMAIL_TOKENS})"
        )
    if saved_file:
        return path
    logger.info(
        "%s Tokens cobranza@ guardados en BD (clave %s)",
        CONFIG_LOG_PREFIX,
        CLAVE_COBRANZA_GMAIL_TOKENS,
    )
    return f"postgresql:{CLAVE_COBRANZA_GMAIL_TOKENS}"


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
