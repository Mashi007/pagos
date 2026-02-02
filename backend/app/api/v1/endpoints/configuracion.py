"""
Endpoints de configuración general.
GET/PUT /configuracion/general, GET /configuracion/logo/{filename},
POST /configuracion/upload-logo, DELETE /configuracion/logo.
Sub-router /configuracion/ai para OpenRouter (clave solo en backend).
Configuración general y logo se persisten en BD (tabla configuracion) para que
funcione en Render sin LOGO_UPLOAD_DIR y sobreviva reinicios y múltiples workers.
"""
import base64
import json
import logging
import os
import re
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_user
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.endpoints import configuracion_ai, configuracion_email, configuracion_whatsapp, configuracion_informe_pagos
from app.core.database import get_db
from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)
# Router con auth para todo excepto logo (general, upload, delete, sub-routers)
router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(configuracion_ai.router, prefix="/ai", tags=["configuracion-ai"])
router.include_router(configuracion_email.router, prefix="/email", tags=["configuracion-email"])
router.include_router(configuracion_whatsapp.router, prefix="/whatsapp", tags=["configuracion-whatsapp"])
router.include_router(configuracion_informe_pagos.router, prefix="/informe-pagos", tags=["configuracion-informe-pagos"])

# Router sin auth para GET/HEAD logo (login, correos, etc. pueden cargar el logo sin token)
router_logo = APIRouter()

CLAVE_CONFIG_GENERAL = "configuracion_general"
CLAVE_LOGO_IMAGEN = "logo_imagen"

# Stub en memoria (alineado con frontend ConfiguracionGeneral). Se sincroniza con BD.
_config_stub: dict[str, Any] = {
    "nombre_empresa": "RapiCredit",
    "ruc": "",
    "direccion": "",
    "telefono": "",
    "email": "",
    "horario_atencion": "",
    "zona_horaria": "America/Caracas",
    "formato_fecha": "DD/MM/YYYY",
    "idioma": "ES",
    "moneda": "VES",
    "version_sistema": "1.0.0",
    "logo_filename": None,
}


def _logo_dir() -> Optional[str]:
    base_dir = os.environ.get("LOGO_UPLOAD_DIR")
    if base_dir and os.path.isdir(base_dir):
        return base_dir
    return None


def _safe_filename(name: str) -> str:
    """Solo permite caracteres seguros para nombre de archivo (evita path traversal)."""
    if not name or not name.strip():
        return ""
    base = os.path.basename(name)
    base = re.sub(r"[^\w.\-]", "_", base)
    return base[:200] or "logo"


def _load_general_from_db(db: Session) -> None:
    """Carga configuración general desde la tabla configuracion y la fusiona en el stub."""
    try:
        row = db.get(Configuracion, CLAVE_CONFIG_GENERAL)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in _config_stub and v is not None:
                        _config_stub[k] = v
    except Exception:
        pass


def _save_general_to_db(db: Session) -> None:
    """Guarda el stub de configuración general en la tabla configuracion."""
    try:
        payload = json.dumps(_config_stub)
        row = db.get(Configuracion, CLAVE_CONFIG_GENERAL)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_CONFIG_GENERAL, valor=payload))
        db.commit()
    except Exception:
        db.rollback()
        raise


def _content_type_for_filename(filename: str) -> str:
    """Devuelve Content-Type según extensión del logo."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "svg":
        return "image/svg+xml"
    if ext == "png":
        return "image/png"
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    return "image/png"


@router.get("/general")
def get_configuracion_general(db: Session = Depends(get_db)):
    """
    Configuración general. El frontend espera nombre_empresa, logo_filename, version_sistema, idioma, zona_horaria, moneda.
    Se carga desde BD para que persista en Render y entre workers.
    """
    _load_general_from_db(db)
    return _config_stub.copy()


class ConfiguracionGeneralUpdate(BaseModel):
    """Campos permitidos para actualizar configuración general (alineado con frontend)."""
    nombre_empresa: Optional[str] = None
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    horario_atencion: Optional[str] = None
    zona_horaria: Optional[str] = None
    formato_fecha: Optional[str] = None
    idioma: Optional[str] = None
    moneda: Optional[str] = None
    version_sistema: Optional[str] = None


@router.put("/general")
def put_configuracion_general(payload: ConfiguracionGeneralUpdate = Body(...), db: Session = Depends(get_db)):
    """
    Actualizar configuración general. Se persiste en BD.
    """
    _load_general_from_db(db)
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k in _config_stub:
            _config_stub[k] = v
    _save_general_to_db(db)
    logger.info("Configuración general actualizada y persistida en BD (campos: %s)", list(data.keys()))
    return {"message": "Configuración actualizada", "configuracion": _config_stub.copy()}


def _logo_exists_and_type(filename: str, db: Session) -> tuple[bool, Optional[str]]:
    """Comprueba si el logo existe (disco o BD) y devuelve (existe, media_type). Usado por GET y HEAD."""
    safe = _safe_filename(filename)
    if not safe:
        return False, None
    base_dir = _logo_dir()
    if base_dir:
        path = os.path.join(base_dir, safe)
        if os.path.isfile(path) and os.path.normpath(path).startswith(os.path.normpath(base_dir)):
            return True, _content_type_for_filename(safe)
    _load_general_from_db(db)
    if _config_stub.get("logo_filename") != safe:
        return False, None
    row = db.get(Configuracion, CLAVE_LOGO_IMAGEN)
    if not row or not row.valor:
        return False, None
    return True, _content_type_for_filename(safe)


@router_logo.get("/logo/{filename}")
def get_logo(filename: str, db: Session = Depends(get_db)):
    """
    Sirve el logo por nombre de archivo. Primero intenta LOGO_UPLOAD_DIR; si no hay o no existe,
    sirve desde BD (logo_imagen en base64) para que funcione en Render sin disco persistente.
    ⚠️ PÚBLICO: no exige auth (login, correos, preview en Configuración).
    """
    safe = _safe_filename(filename)
    if not safe:
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    base_dir = _logo_dir()
    if base_dir:
        path = os.path.join(base_dir, safe)
        if os.path.isfile(path) and os.path.normpath(path).startswith(os.path.normpath(base_dir)):
            return FileResponse(path)
    _load_general_from_db(db)
    if _config_stub.get("logo_filename") != safe:
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    row = db.get(Configuracion, CLAVE_LOGO_IMAGEN)
    if not row or not row.valor:
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    try:
        content = base64.b64decode(row.valor)
    except Exception:
        raise HTTPException(status_code=500, detail="Logo corrupto")
    media_type = _content_type_for_filename(safe)
    return Response(content=content, media_type=media_type)


@router_logo.head("/logo/{filename}")
def head_logo(filename: str, db: Session = Depends(get_db)):
    """
    HEAD para el logo: el frontend usa HEAD para comprobar si existe sin descargar.
    Sin este endpoint, algunos proxies/dev devuelven 405 Method Not Allowed.
    ⚠️ PÚBLICO: no debe exigir auth (login, correos, etc. cargan el logo sin token).
    Si devuelve 401, revisar que ningún middleware aplique auth a este router.
    """
    exists, media_type = _logo_exists_and_type(filename, db)
    if not exists:
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    return Response(status_code=200, headers={"Content-Type": media_type or "image/png"})


@router.post("/upload-logo")
async def upload_logo(logo: UploadFile = File(..., alias="logo"), db: Session = Depends(get_db)):
    """
    Subir logo de la empresa. Si LOGO_UPLOAD_DIR está configurado, guarda en disco;
    si no (p. ej. Render), guarda el contenido en BD (base64) y logo_filename en config general.
    Retorna { filename, url } para que el frontend muestre el preview.
    """
    if not logo.content_type or not logo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (SVG, PNG, JPG)")
    content = await logo.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo no debe superar 2MB")
    ext = "png"
    if logo.filename and "." in logo.filename:
        ext = logo.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("svg", "png", "jpg", "jpeg"):
        ext = "png"
    filename = f"logo-{uuid.uuid4().hex[:8]}.{ext}"
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    url = f"{base_url}/api/v1/configuracion/logo/{filename}" if base_url else f"/api/v1/configuracion/logo/{filename}"

    _load_general_from_db(db)
    base_dir = _logo_dir()
    if base_dir:
        path = os.path.join(base_dir, filename)
        with open(path, "wb") as f:
            f.write(content)
    else:
        # Sin carpeta: guardar imagen en BD en base64 para servir en GET /logo/{filename}
        try:
            b64 = base64.b64encode(content).decode("ascii")
            row = db.get(Configuracion, CLAVE_LOGO_IMAGEN)
            if row:
                row.valor = b64
            else:
                db.add(Configuracion(clave=CLAVE_LOGO_IMAGEN, valor=b64))
            db.commit()
        except Exception:
            db.rollback()
            raise
    _config_stub["logo_filename"] = filename
    _save_general_to_db(db)
    logger.info("Logo subido y persistido en BD: filename=%s", filename)
    return {"filename": filename, "url": url}


@router.delete("/logo")
def delete_logo(db: Session = Depends(get_db)):
    """
    Eliminar logo actual. Borra archivo en disco si existe y/o fila logo_imagen en BD.
    Persiste logo_filename=None en configuración general.
    """
    _load_general_from_db(db)
    base_dir = _logo_dir()
    fn = _config_stub.get("logo_filename")
    if fn and base_dir:
        path = os.path.join(base_dir, _safe_filename(fn))
        if os.path.isfile(path) and os.path.normpath(path).startswith(os.path.normpath(base_dir)):
            try:
                os.remove(path)
            except OSError:
                pass
    # Eliminar logo de BD si existía
    try:
        row = db.get(Configuracion, CLAVE_LOGO_IMAGEN)
        if row:
            db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
    _config_stub["logo_filename"] = None
    _save_general_to_db(db)
    return {"message": "Logo eliminado. Se usará el logo por defecto."}


# --- Configuración desde BD (tabla configuracion) ---

CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"


@router.get("/notificaciones/envios")
def get_notificaciones_envios(db: Session = Depends(get_db)):
    """Configuración de envíos por tipo (habilitado, cco). Datos desde BD."""
    try:
        row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


@router.put("/notificaciones/envios")
def put_notificaciones_envios(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actualizar configuración de envíos. Persiste en BD."""
    try:
        valor = json.dumps(payload)
        row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
        if row:
            row.valor = valor
        else:
            db.add(Configuracion(clave=CLAVE_NOTIFICACIONES_ENVIOS, valor=valor))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"message": "Configuración de envíos actualizada", "configuracion": payload}


@router.post("/validadores/probar")
def post_validadores_probar(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Probar validadores con datos de ejemplo. Devuelve resultados; sin datos mock."""
    from datetime import datetime
    return {
        "titulo": "Prueba de validadores",
        "fecha_prueba": datetime.utcnow().isoformat() + "Z",
        "datos_entrada": payload,
        "resultados": {},
        "resumen": {"total_validados": 0, "validos": 0, "invalidos": 0},
    }


@router.get("/sistema/completa")
def get_sistema_completa(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    """Configuración completa del sistema desde BD."""
    _load_general_from_db(db)
    return {"data": _config_stub.copy()}


@router.get("/sistema/categoria/{categoria}")
def get_sistema_categoria(categoria: str, db: Session = Depends(get_db)):
    """Configuración por categoría desde BD."""
    _load_general_from_db(db)
    return {"data": _config_stub.copy()}
