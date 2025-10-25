"""
"""

import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.concesionario import Concesionario
from app.models.user import User
from app.schemas.concesionario import (
    ConcesionarioCreate,
    ConcesionarioListResponse,
    ConcesionarioResponse,
    ConcesionarioUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test-no-auth")
    """
    """
    try:


        return {
            "success": True,
        }
    except Exception as e:
        logger.error(
        )
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/test-simple")
    """
    """
    try:


        return {
            "success": True,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/test-auth")
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    try:
        return {
            "success": True,
            "user": current_user.email,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/list-no-auth")
    limit: int = Query(
    ),
    activo: Optional[bool] = Query(
        None, description="Filtrar por estado activo"
    ),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
):
    """
    """
    try:
        query = db.query(Concesionario)

        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))

        # Obtener total
        total = query.count()

        # Aplicar paginación

        # Calcular páginas
        pages = (total + limit - 1) // limit

        return {
            "items": [
            ],
            "total": total,
            "page": (skip // limit) + 1,
            "size": limit,
            "pages": pages,
        }
    except Exception as e:
        raise HTTPException(
        )


@router.get("/", response_model=ConcesionarioListResponse)
    limit: int = Query(
    ),
    activo: Optional[bool] = Query(
        None, description="Filtrar por estado activo"
    ),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    """
    try:
        query = db.query(Concesionario)

        if activo is not None:
            query = query.filter(Concesionario.activo == activo)
        if search:
            query = query.filter(Concesionario.nombre.ilike(f"%{search}%"))

        # Obtener total
        total = query.count()

        # Aplicar paginación

        # Calcular páginas
        pages = (total + limit - 1) // limit

        return ConcesionarioListResponse(
            items=[
            ],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages,
        )
    except Exception as e:
        raise HTTPException(
        )


    db: Session = Depends(get_db),
    # TEMPORALMENTE SIN AUTENTICACIÓN PARA DROPDOWNS
    # current_user: User = Depends(get_current_user)
):
    """
    """
    try:
            db.query(Concesionario).filter(Concesionario.activo).all()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
        )


@router.get("/{concesionario_id}", response_model=ConcesionarioResponse)
def obtener_concesionario(
    concesionario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Obtener un concesionario por ID
    """
    concesionario = (
        db.query(Concesionario)
        .filter(Concesionario.id == concesionario_id)
        .first()
    )
    if not concesionario:
        raise HTTPException(
            status_code=404, detail="Concesionario no encontrado"
        )
    return ConcesionarioResponse.model_validate(concesionario)


def crear_concesionario(
    concesionario_data: ConcesionarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ➕ Crear un nuevo concesionario
    """
    try:
        # Crear nuevo concesionario
        concesionario = Concesionario(
            nombre=concesionario_data.nombre,
            activo=concesionario_data.activo,
        )

        db.add(concesionario)
        db.commit()
        db.refresh(concesionario)

        logger.info(f"Concesionario creado: ID={concesionario.id}")
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando concesionario: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al crear concesionario: {str(e)}"
        )


@router.put("/{concesionario_id}", response_model=ConcesionarioResponse)
def actualizar_concesionario(
    concesionario_id: int,
    concesionario_data: ConcesionarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✏️ Actualizar un concesionario existente
    """
    try:
        concesionario = (
            db.query(Concesionario)
            .filter(Concesionario.id == concesionario_id)
            .first()
        )
        if not concesionario:
            raise HTTPException(
                status_code=404, detail="Concesionario no encontrado"
            )

        # Verificar nombre único si se está cambiando
        if (
            concesionario_data.nombre
            and concesionario_data.nombre != concesionario.nombre
        ):
            existing = (
                db.query(Concesionario)
                .filter(
                    Concesionario.nombre == concesionario_data.nombre,
                    Concesionario.id != concesionario_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe un concesionario con este nombre",
                )

        update_data = concesionario_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(concesionario, field, value)

        db.commit()
        db.refresh(concesionario)
        return ConcesionarioResponse.model_validate(concesionario)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar concesionario: {str(e)}",
        )


@router.delete("/{concesionario_id}")
def eliminar_concesionario(
    concesionario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🗑️ Eliminar un concesionario (HARD DELETE - borrado completo de BD)
    """
    try:
        concesionario = (
            db.query(Concesionario)
            .filter(Concesionario.id == concesionario_id)
            .first()
        )
        if not concesionario:
            raise HTTPException(
                status_code=404, detail="Concesionario no encontrado"
            )

        db.delete(concesionario)
        db.commit()

        return {
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar concesionario: {str(e)}",
        )
