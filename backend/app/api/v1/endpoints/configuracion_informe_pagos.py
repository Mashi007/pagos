"""
GET/PUT configuración informe de pagos (Google Drive, Sheets, OCR, destinatarios email, horarios).
Usado por flujo cobranza WhatsApp: imágenes → Drive → OCR → digitalización → email 6:00, 13:00, 16:30.
OAuth para Drive/Sheets cuando la organización no permite claves de cuenta de servicio.
"""
import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx

from app.core.deps import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.core.informe_pagos_config_holder import (
    CLAVE_INFORME_PAGOS_CONFIG,
    get_informe_pagos_config,
    get_google_oauth_client_id,
    get_google_oauth_client_secret,
    sync_from_db,
    update_from_api,
)
from app.models.configuracion import Configuracion
from app.models.user import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# Router público para el callback de Google (sin auth)
router_google_callback = APIRouter()


class InformePagosConfigUpdate(BaseModel):
    """Campos permitidos para informe de pagos (Google Drive, Sheets, OCR, email)."""
    google_drive_folder_id: Optional[str] = None
    google_credentials_json: Optional[str] = None
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    google_sheets_id: Optional[str] = None
    destinatarios_informe_emails: Optional[str] = None
    horarios_envio: Optional[list] = None


GOOGLE_OAUTH_SCOPES = " ".join([
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/cloud-vision",  # OCR (Vision API)
])
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _backend_base_url() -> str:
    """URL base del backend para redirect_uri (sin barra final)."""
    url = (getattr(settings, "BACKEND_PUBLIC_URL", None) or "").strip()
    if url:
        return url.rstrip("/")
    return "https://pagos-f2qf.onrender.com"


@router.get("/google/authorize")
def google_oauth_authorize(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Redirige al usuario a Google para autorizar acceso a Drive y Sheets.
    Tras autorizar, Google redirige a /google/callback; ahí se guarda el refresh_token.
    """
    sync_from_db()
    client_id = get_google_oauth_client_id()
    if not client_id:
        return {"detail": "Configura primero Client ID y Client Secret en Informe pagos (OAuth)."}
    state = secrets.token_urlsafe(32)
    base = _backend_base_url()
    redirect_uri = f"{base}{settings.API_V1_STR}/configuracion/informe-pagos/google/callback"
    # Guardar state en BD (clave temporal)
    state_key = f"google_oauth_state_{state}"
    state_val = json.dumps({"user_id": current_user.id, "created_at": datetime.utcnow().isoformat()})
    row = db.get(Configuracion, state_key)
    if row:
        row.valor = state_val
    else:
        db.add(Configuracion(clave=state_key, valor=state_val))
    db.commit()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_OAUTH_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@router_google_callback.get("/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Callback de Google OAuth. Intercambia code por tokens y guarda refresh_token en informe_pagos_config.
    Redirige al frontend con ?google_oauth=ok o ?google_oauth=error.
    """
    redirect_ok = "https://rapicredit.onrender.com/pagos/configuracion?tab=informe-pagos&google_oauth=ok"
    redirect_fail = "https://rapicredit.onrender.com/pagos/configuracion?tab=informe-pagos&google_oauth=error"
    if error or not code or not state:
        logger.warning("Google OAuth callback error o sin code/state: error=%s", error)
        return RedirectResponse(url=redirect_fail, status_code=302)
    state_key = f"google_oauth_state_{state}"
    row = db.get(Configuracion, state_key)
    if not row or not row.valor:
        logger.warning("Google OAuth state no encontrado o expirado")
        return RedirectResponse(url=redirect_fail, status_code=302)
    try:
        data = json.loads(row.valor)
        created = datetime.fromisoformat(data["created_at"])
        if datetime.utcnow() - created > timedelta(minutes=10):
            db.delete(row)
            db.commit()
            logger.warning("Google OAuth state expirado")
            return RedirectResponse(url=redirect_fail, status_code=302)
    except Exception:
        db.delete(row)
        db.commit()
        return RedirectResponse(url=redirect_fail, status_code=302)
    db.delete(row)
    db.commit()
    sync_from_db()
    client_id = get_google_oauth_client_id()
    client_secret = get_google_oauth_client_secret()
    if not client_id or not client_secret:
        logger.warning("Google OAuth: client_id o client_secret no configurados")
        return RedirectResponse(url=redirect_fail, status_code=302)
    base = _backend_base_url()
    redirect_uri = f"{base}{settings.API_V1_STR}/configuracion/informe-pagos/google/callback"
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client() as client:
            r = client.post(GOOGLE_TOKEN_URI, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15.0)
            r.raise_for_status()
            tokens = r.json()
    except Exception as e:
        logger.exception("Google OAuth token exchange failed: %s", e)
        return RedirectResponse(url=redirect_fail, status_code=302)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        logger.warning("Google OAuth: no refresh_token in response")
        return RedirectResponse(url=redirect_fail, status_code=302)
    cfg = get_informe_pagos_config()
    cfg["google_oauth_refresh_token"] = refresh_token
    update_from_api(cfg)
    valor = json.dumps(get_informe_pagos_config())
    config_row = db.get(Configuracion, CLAVE_INFORME_PAGOS_CONFIG)
    if config_row:
        config_row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_INFORME_PAGOS_CONFIG, valor=valor))
    db.commit()
    logger.info("Google OAuth refresh_token guardado correctamente")
    return RedirectResponse(url=redirect_ok, status_code=302)


def _verificar_drive() -> dict:
    """Prueba real de conexión a Google Drive: subir un archivo de prueba y borrarlo."""
    import io
    from app.core.informe_pagos_config_holder import get_google_drive_folder_id, use_google_oauth
    from app.core.google_credentials import get_google_credentials

    folder_id = get_google_drive_folder_id()
    creds = get_google_credentials(["https://www.googleapis.com/auth/drive.file"])
    if not creds:
        detalle = "Sin credenciales (cuenta de servicio JSON u OAuth con 'Conectar con Google')."
        if use_google_oauth():
            detalle = (
                "Token OAuth expirado o revocado. Haz clic en 'Conectar con Google' de nuevo en esta sección."
            )
        return {"conectado": False, "detalle": detalle}
    if not folder_id:
        return {"conectado": False, "detalle": "No hay ID de carpeta configurado. Indica el ID de la carpeta de Drive en la configuración."}
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        drive = build("drive", "v3", credentials=creds)
        meta = {"name": "_test_conexion_pagos.txt", "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(b"ok"), mimetype="text/plain", resumable=False)
        f = drive.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = f.get("id")
        if file_id:
            drive.files().delete(fileId=file_id).execute()
        return {"conectado": True, "detalle": "Conexión correcta. La carpeta es accesible para subir imágenes."}
    except Exception as e:
        logger.debug("Verificación Drive fallida: %s", e, exc_info=True)
        msg = str(e).strip() or "Error desconocido"
        if "404" in msg or "not found" in msg.lower():
            return {"conectado": False, "detalle": "Carpeta no encontrada o sin acceso. Comprueba el ID de carpeta y que esté compartida con la cuenta de servicio (email del JSON) o con la cuenta que usaste en 'Conectar con Google'."}
        if "403" in msg or "permission" in msg.lower() or "forbidden" in msg.lower():
            return {"conectado": False, "detalle": "Sin permiso. Comparte la carpeta en Drive con rol Editor: con el email de la cuenta de servicio (client_email del JSON) o con la cuenta Google que autorizaste."}
        return {"conectado": False, "detalle": f"Error: {msg[:200]}"}


def _verificar_sheets() -> dict:
    """Prueba real de conexión a Google Sheets: lectura de metadatos y escritura de una fila de prueba (luego se borra)."""
    from app.core.informe_pagos_config_holder import get_google_sheets_id, use_google_oauth
    from app.core.google_credentials import get_google_credentials

    sheet_id = get_google_sheets_id()
    creds = get_google_credentials(["https://www.googleapis.com/auth/spreadsheets"])
    if not creds:
        detalle = "Sin credenciales (cuenta de servicio JSON u OAuth con 'Conectar con Google')."
        if use_google_oauth():
            detalle = "Token OAuth expirado o revocado. Haz clic en 'Conectar con Google' de nuevo en esta sección."
        return {"conectado": False, "detalle": detalle}
    if not sheet_id:
        return {"conectado": False, "detalle": "No hay ID de hoja configurado."}
    try:
        from googleapiclient.discovery import build
        service = build("sheets", "v4", credentials=creds)
        # 1) Lectura: comprobar que la hoja existe y tenemos acceso
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet.get("sheets") or []
        if not sheets:
            return {"conectado": False, "detalle": "La hoja no tiene pestañas. Añade al menos una pestaña."}
        first_sheet = sheets[0]
        tab_title = (first_sheet.get("properties") or {}).get("title") or "Hoja 1"
        # 2) Escritura: escribir una fila de prueba en fila 1000 (no tocar cabeceras) y borrarla
        range_write = f"'{tab_title}'!A1000:G1000"
        body = {"values": [["_verif_conexion", datetime.utcnow().isoformat(), "", "", "", "", ""]]}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_write,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=range_write,
            body={},
        ).execute()
        return {"conectado": True, "detalle": "Conexión correcta. La hoja es accesible para lectura y escritura (informe de pagos)."}
    except Exception as e:
        logger.debug("Verificación Sheets fallida: %s", e, exc_info=True)
        msg = str(e).strip() or "Error desconocido"
        if "404" in msg or "not found" in msg.lower():
            return {"conectado": False, "detalle": "Hoja no encontrada o sin acceso. Comprueba el ID y que la hoja esté compartida con la cuenta."}
        if "403" in msg or "permission" in msg.lower() or "forbidden" in msg.lower():
            return {"conectado": False, "detalle": "Sin permiso. Comparte la hoja con rol Editor con la cuenta de servicio (client_email del JSON) o con la cuenta que usaste en 'Conectar con Google'."}
        return {"conectado": False, "detalle": f"Error: {msg[:200]}"}


def _verificar_ocr() -> dict:
    """Prueba real de conexión a Google Cloud Vision (OCR). Una llamada mínima a la API."""
    from app.core.informe_pagos_config_holder import use_google_oauth
    from app.core.google_credentials import get_google_credentials

    creds = get_google_credentials(["https://www.googleapis.com/auth/cloud-vision"])
    if not creds:
        detalle = "Sin credenciales (cuenta de servicio JSON u OAuth con 'Conectar con Google')."
        if use_google_oauth():
            detalle = "Token OAuth expirado o revocado. Haz clic en 'Conectar con Google' de nuevo en esta sección."
        return {"conectado": False, "detalle": detalle}
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient(credentials=creds)
        # Imagen mínima 1x1 pixel JPEG para no gastar ancho de banda; la API responde aunque no haya texto
        minimal_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.7\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x00\x01\xff\xd9"
        image = vision.Image(content=minimal_jpeg)
        client.text_detection(image=image)
        return {"conectado": True, "detalle": "Conexión correcta. Vision API (OCR) operativa."}
    except Exception as e:
        msg = str(e).strip() or "Error desconocido"
        if "403" in msg or "permission" in msg.lower() or "forbidden" in msg.lower() or "Vision API has not been used" in msg:
            return {"conectado": False, "detalle": "Vision API no habilitada o sin permiso. Actívala en Google Cloud Console para el proyecto."}
        return {"conectado": False, "detalle": f"Error: {msg[:200]}"}


@router.get("/estado")
def get_estado_conexiones(db: Session = Depends(get_db)):
    """
    Verifica con llamadas reales si Drive, Sheets y OCR (Vision) están conectados y operativos.
    Devuelve para cada uno: conectado (bool) y detalle (mensaje para el usuario).
    """
    sync_from_db()
    return {
        "drive": _verificar_drive(),
        "sheets": _verificar_sheets(),
        "ocr": _verificar_ocr(),
    }


@router.get("/configuracion", response_model=dict)
def get_informe_pagos_configuracion(db: Session = Depends(get_db)):
    """
    Configuración informe de pagos (Google Drive, Sheets, OCR, destinatarios, horarios).
    google_credentials_json se devuelve enmascarado (***) por seguridad.
    """
    sync_from_db()
    cfg = get_informe_pagos_config()
    out = dict(cfg)
    if out.get("google_credentials_json"):
        out["google_credentials_json"] = "***"
    if out.get("google_oauth_client_secret"):
        out["google_oauth_client_secret"] = "***"
    # No exponer refresh_token al frontend; solo indicar si OAuth está conectado
    if "google_oauth_refresh_token" in out and out["google_oauth_refresh_token"]:
        out["google_oauth_refresh_token"] = "***"
    return out


@router.put("/configuracion", response_model=dict)
def put_informe_pagos_configuracion(
    payload: InformePagosConfigUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """
    Actualizar configuración informe de pagos. Persiste en BD (clave informe_pagos_config).
    - google_credentials_json: si envías "***" o no envías la clave, no se sobrescribe.
      Si envías "" (cadena vacía), se limpia el campo (para usar solo OAuth).
    """
    sync_from_db()
    data = payload.model_dump(exclude_none=True)
    # Solo no sobrescribir cuando es "***" o la clave no viene; "" sí limpia el campo
    if data.get("google_credentials_json") == "***":
        data.pop("google_credentials_json", None)
    update_from_api(data)
    valor = json.dumps(get_informe_pagos_config())
    row = db.get(Configuracion, CLAVE_INFORME_PAGOS_CONFIG)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_INFORME_PAGOS_CONFIG, valor=valor))
    db.commit()
    logger.info("Configuración informe pagos actualizada (campos: %s)", list(data.keys()))
    out = get_informe_pagos_config()
    if out.get("google_credentials_json"):
        out["google_credentials_json"] = "***"
    if out.get("google_oauth_client_secret"):
        out["google_oauth_client_secret"] = "***"
    if "google_oauth_refresh_token" in out and out["google_oauth_refresh_token"]:
        out["google_oauth_refresh_token"] = "***"
    return {"message": "Configuración informe pagos actualizada", "configuracion": out}
