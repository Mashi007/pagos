"""
Endpoints de configuración general (stub para que el frontend no reciba 404).
GET /configuracion/general y GET /configuracion/logo/{filename} para Logo y Configuración.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()


@router.get("/general")
def get_configuracion_general():
    """
    Configuración general (stub). El frontend espera al menos logo_filename y opcionalmente nombre_app.
    Sin base de datos se devuelve un objeto mínimo; el logo se puede servir después si existe archivo.
    """
    return {
        "nombre_app": "RapiCredit",
        "logo_filename": None,
    }


@router.get("/logo/{filename}")
def get_logo(filename: str):
    """
    Sirve el logo por nombre de archivo. Si no hay archivo subido, 404 (el frontend usa logo por defecto).
    Para implementación real: guardar logos en carpeta estática o almacenamiento y servir desde aquí.
    """
    # Opcional: buscar en una carpeta uploads/logos si existe
    base_dir = os.environ.get("LOGO_UPLOAD_DIR")
    if base_dir and os.path.isdir(base_dir):
        path = os.path.join(base_dir, filename)
        if os.path.isfile(path):
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="Logo no encontrado")
