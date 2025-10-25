from datetime import date
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
from app.schemas.concesionario import 

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test-no-auth")
    """
    """
    try:


        return 
    except Exception as e:
        logger.error
        return 


@router.get("/test-simple")
    """
    """
    try:


        return 
    except Exception as e:
        return 


@router.get("/test-auth")
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """
    """
    try:
        return 
    except Exception as e:
        return 


@router.get("/list-no-auth")
    limit: int = Query
    activo: Optional[bool] = Query
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
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

        return 
    except Exception as e:
        raise HTTPException


@router.get("/", response_model=ConcesionarioListResponse)
    limit: int = Query
    activo: Optional[bool] = Query
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

        return ConcesionarioListResponse
            page=(skip // limit) + 1,
            size=limit,
            pages=pages,
    except Exception as e:
        raise HTTPException


    db: Session = Depends(get_db),
    # TEMPORALMENTE SIN AUTENTICACIÓN PARA DROPDOWNS
    # current_user: User = Depends(get_current_user)
    """
    """
    try:
            db.query(Concesionario).filter(Concesionario.activo).all()
    except Exception as e:
        raise HTTPException


@router.get("/{concesionario_id}", response_model=ConcesionarioResponse)
def obtener_concesionario
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """
    🔍 Obtener un concesionario por ID
    """
    concesionario = 
        db.query(Concesionario)
        .filter(Concesionario.id == concesionario_id)
        .first()
    if not concesionario:
        raise HTTPException
    return ConcesionarioResponse.model_validate(concesionario)


def crear_concesionario
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """
    ➕ Crear un nuevo concesionario
    """
    try:
        # Crear nuevo concesionario
        concesionario = Concesionario

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
        raise HTTPException
            status_code=500, detail=f"Error al crear concesionario: {str(e)}"


@router.put("/{concesionario_id}", response_model=ConcesionarioResponse)
def actualizar_concesionario
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """
    ✏️ Actualizar un concesionario existente
    """
    try:
        concesionario = 
            db.query(Concesionario)
            .filter(Concesionario.id == concesionario_id)
            .first()
        if not concesionario:
            raise HTTPException

        # Verificar nombre único si se está cambiando
        if 
            existing = 
                db.query(Concesionario)
                .filter
                .first()
            if existing:
                raise HTTPException

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
        raise HTTPException
            detail=f"Error al actualizar concesionario: {str(e)}",


@router.delete("/{concesionario_id}")
def eliminar_concesionario
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """
    🗑️ Eliminar un concesionario (HARD DELETE - borrado completo de BD)
    """
    try:
        concesionario = 
            db.query(Concesionario)
            .filter(Concesionario.id == concesionario_id)
            .first()
        if not concesionario:
            raise HTTPException

        db.delete(concesionario)
        db.commit()

        return 

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException
            detail=f"Error al eliminar concesionario: {str(e)}",
