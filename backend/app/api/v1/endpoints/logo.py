"""
Endpoints para manejo de logo de la empresa
Almacena el logo en PostgreSQL como BYTEA
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.logo import Logo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

LOGO_NAME = "logo_principal"  # Nombre del logo en la BD


@router.get("/logo")
def obtener_logo(db: Session = Depends(get_db)):
    """
    Obtener el logo de la empresa desde PostgreSQL
    """
    try:
        logo = db.query(Logo).filter(Logo.nombre == LOGO_NAME).first()

        if not logo:
            raise HTTPException(status_code=404, detail="Logo no encontrado")

        return Response(
            content=logo.archivo,
            media_type=logo.tipo_mime,
            headers={"Content-Disposition": f"inline; filename={logo.nombre}"},
        )

    except HTTPException:
        raise
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
    Subir o actualizar el logo de la empresa en PostgreSQL
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

        # Leer contenido del archivo
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB max
            raise HTTPException(
                status_code=400,
                detail="El archivo es demasiado grande (máximo 5MB)",
            )

        # Buscar si ya existe un logo
        logo = db.query(Logo).filter(Logo.nombre == LOGO_NAME).first()

        if logo:
            # Actualizar logo existente
            logo.archivo = content
            logo.tipo_mime = file.content_type
            logo.subido_por = current_user.id
        else:
            # Crear nuevo logo
            logo = Logo(
                nombre=LOGO_NAME,
                archivo=content,
                tipo_mime=file.content_type,
                subido_por=current_user.id,
            )
            db.add(logo)

        db.commit()
        db.refresh(logo)

        logger.info(f"Logo actualizado por: {current_user.email}")

        return {
            "message": "Logo actualizado exitosamente",
            "filename": file.filename,
            "size": len(content),
            "tipo_mime": file.content_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
    Eliminar el logo de la empresa desde PostgreSQL
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden eliminar logos",
        )

    try:
        logo = db.query(Logo).filter(Logo.nombre == LOGO_NAME).first()

        if not logo:
            raise HTTPException(status_code=404, detail="Logo no encontrado")

        db.delete(logo)
        db.commit()

        logger.info(f"Logo eliminado por: {current_user.email}")
        return {"message": "Logo eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando logo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
