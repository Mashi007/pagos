import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.pago import Pago
from app.models.user import User
from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuración de archivos
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


@router.post(
    "/crear", response_model=PagoResponse, status_code=status.HTTP_201_CREATED
)
async def crear_pago(
    pago_data: PagoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear un nuevo pago
    try:
        logger.info(f"Creando pago - Usuario: {current_user.email}")

        # Crear el pago
        nuevo_pago = Pago(**pago_data.model_dump())

        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)

        return nuevo_pago

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando pago: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.get("/", response_model=list[PagoResponse])
def listar_pagos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar pagos con paginación
    try:
        pagos = db.query(Pago).offset(skip).limit(limit).all()
        return pagos
        
    except Exception as e:
        logger.error(f"Error listando pagos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{pago_id}", response_model=PagoResponse)
def obtener_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener pago específico
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        
        if not pago:
            raise HTTPException(
                status_code=404,
                detail="Pago no encontrado"
            )
        
        return pago
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo pago: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{pago_id}", response_model=PagoResponse)
def actualizar_pago(
    pago_id: int,
    pago_data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar pago
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        
        if not pago:
            raise HTTPException(
                status_code=404,
                detail="Pago no encontrado"
            )
        
        # Actualizar campos
        for field, value in pago_data.model_dump(exclude_unset=True).items():
            setattr(pago, field, value)
        
        db.commit()
        db.refresh(pago)
        
        return pago
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando pago: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/{pago_id}")
def eliminar_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar pago
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        
        if not pago:
            raise HTTPException(
                status_code=404,
                detail="Pago no encontrado"
            )
        
        db.delete(pago)
        db.commit()
        
        return {"message": "Pago eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando pago: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/subir-documento")
async def subir_documento(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Subir documento de pago
    try:
        # Validar tipo de archivo
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Solo se permiten: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Validar tamaño
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
            )

        # Generar nombre único
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_extension}"
        
        # Guardar archivo
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return {
            "message": "Archivo subido exitosamente",
            "file_id": file_id,
            "filename": filename,
            "size": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo archivo: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )