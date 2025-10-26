import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.prestamo import PrestamoCreate, PrestamoResponse, PrestamoUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_prestamo(
    prestamo_data: PrestamoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo préstamo
    try:
        nuevo_prestamo = Prestamo(**prestamo_data.model_dump())
        nuevo_prestamo.creado_por = current_user.id

        db.add(nuevo_prestamo)
        db.commit()
        db.refresh(nuevo_prestamo)

        return nuevo_prestamo

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando préstamo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/", response_model=List[PrestamoResponse])
def listar_prestamos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar préstamos con paginación
    try:
        prestamos = db.query(Prestamo).offset(skip).limit(limit).all()
        return prestamos

    except Exception as e:
        logger.error(f"Error listando préstamos: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{prestamo_id}", response_model=PrestamoResponse)
def obtener_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener préstamo específico
    try:
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        return prestamo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo préstamo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{prestamo_id}", response_model=PrestamoResponse)
def actualizar_prestamo(
    prestamo_id: int,
    prestamo_data: PrestamoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar préstamo
    try:
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        # Actualizar campos
        for field, value in prestamo_data.model_dump(exclude_unset=True).items():
            setattr(prestamo, field, value)

        db.commit()
        db.refresh(prestamo)

        return prestamo

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando préstamo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/{prestamo_id}")
def eliminar_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar préstamo
    try:
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        db.delete(prestamo)
        db.commit()

        return {"message": "Préstamo eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando préstamo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
