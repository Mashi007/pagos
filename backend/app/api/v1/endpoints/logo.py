"""
Endpoints para manejo de logo de la empresa
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Directorio para almacenar logos
LOGO_DIR = Path("uploads/logos")
LOGO_DIR.mkdir(parents=True, exist_ok=True)
LOGO_FILE = LOGO_DIR / "logo.png"


@router.get("/logo")
def obtener_logo():
    """
    Obtener el logo de la empresa
    """
    try:
        if LOGO_FILE.exists():
            return FileResponse(str(LOGO_FILE), media_type="image/png")
        else:
            # Retornar un logo por defecto o 404
            raise HTTPException(status_code=404, detail="Logo no encontrado")
    except Exception as e:
        logger.error(f"Error obteniendo logo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/logo")
def subir_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Subir o actualizar el logo de la empresa
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden subir logos",
        )

    try:
        # Validar que es una imagen
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="El archivo debe ser una imagen"
            )

        # Guardar archivo
        with open(LOGO_FILE, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        logger.info(f"Logo actualizado por: {current_user.email}")

        return {
            "message": "Logo actualizado exitosamente",
            "filename": file.filename,
            "size": len(content),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo logo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/logo")
def eliminar_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar el logo de la empresa
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden eliminar logos",
        )

    try:
        if LOGO_FILE.exists():
            LOGO_FILE.unlink()
            logger.info(f"Logo eliminado por: {current_user.email}")
            return {"message": "Logo eliminado exitosamente"}
        else:
            raise HTTPException(status_code=404, detail="Logo no encontrado")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando logo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
