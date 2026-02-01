"""
Endpoints de configuración general.
GET/PUT /configuracion/general, GET /configuracion/logo/{filename},
POST /configuracion/upload-logo, DELETE /configuracion/logo.
Articulado con el frontend (Configuracion.tsx, configuracionGeneralService).
Sin BD: datos en memoria/archivo; cuando exista BD usar get_db y modelos.
"""
import os
import re
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()

# Stub en memoria hasta tener BD (nombre_empresa alineado con frontend ConfiguracionGeneral)
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


@router.get("/general")
def get_configuracion_general():
    """
    Configuración general. El frontend espera nombre_empresa, logo_filename, version_sistema, idioma, zona_horaria, moneda.
    Sin BD se devuelve stub; con BD leer desde tabla de configuración.
    """
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
def put_configuracion_general(payload: ConfiguracionGeneralUpdate = Body(...)):
    """
    Actualizar configuración general (stub). Frontend envía nombre_empresa, idioma, zona_horaria, moneda.
    Sin BD se actualiza stub en memoria; con BD persistir en tabla de configuración.
    """
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if k in _config_stub:
            _config_stub[k] = v
    return {"message": "Configuración actualizada", "configuracion": get_configuracion_general()}


@router.get("/logo/{filename}")
def get_logo(filename: str):
    """
    Sirve el logo por nombre de archivo. Filename saneado para evitar path traversal.
    Si no hay archivo subido, 404 (el frontend usa logo por defecto).
    """
    safe = _safe_filename(filename)
    if not safe:
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    base_dir = _logo_dir()
    if base_dir:
        path = os.path.join(base_dir, safe)
        if os.path.isfile(path) and os.path.normpath(path).startswith(os.path.normpath(base_dir)):
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="Logo no encontrado")


@router.post("/upload-logo")
async def upload_logo(logo: UploadFile = File(..., alias="logo")):
    """
    Subir logo de la empresa. Guarda en LOGO_UPLOAD_DIR si está configurado.
    Retorna { filename, url } para que el frontend muestre el preview y guarde en BD cuando exista.
    """
    if not logo.content_type or not logo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (SVG, PNG, JPG)")
    base_dir = _logo_dir()
    if not base_dir:
        # Sin carpeta configurada: devolver nombre ficticio para que el frontend no falle
        ext = "png"
        if logo.filename and "." in logo.filename:
            ext = logo.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("svg", "png", "jpg", "jpeg"):
            ext = "png"
        filename = f"logo-{uuid.uuid4().hex[:8]}.{ext}"
        base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
        url = f"{base_url}/api/v1/configuracion/logo/{filename}" if base_url else f"/api/v1/configuracion/logo/{filename}"
        return {"filename": filename, "url": url}
    ext = "png"
    if logo.filename and "." in logo.filename:
        ext = logo.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("svg", "png", "jpg", "jpeg"):
        ext = "png"
    filename = f"logo-{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(base_dir, filename)
    content = await logo.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo no debe superar 2MB")
    with open(path, "wb") as f:
        f.write(content)
    _config_stub["logo_filename"] = filename
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    url = f"{base_url}/api/v1/configuracion/logo/{filename}" if base_url else f"/api/v1/configuracion/logo/{filename}"
    return {"filename": filename, "url": url}


@router.delete("/logo")
def delete_logo():
    """
    Eliminar logo actual. Limpia logo_filename en configuración y borra archivo si existe.
    Retorna mensaje para el frontend.
    """
    base_dir = _logo_dir()
    fn = _config_stub.get("logo_filename")
    if fn and base_dir:
        path = os.path.join(base_dir, _safe_filename(fn))
        if os.path.isfile(path) and os.path.normpath(path).startswith(os.path.normpath(base_dir)):
            try:
                os.remove(path)
            except OSError:
                pass
    _config_stub["logo_filename"] = None
    return {"message": "Logo eliminado. Se usará el logo por defecto."}
