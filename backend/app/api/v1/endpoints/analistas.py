import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.analista import Analista
from app.models.user import User
from app.schemas.analista import (
    AnalistaCreate,
    AnalistaListResponse,
    AnalistaResponse,
    AnalistaUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=AnalistaListResponse)
def listar_analistas(
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar analistas con filtros
    try:
        query = db.query(Analista)

        if activo is not None:
            query = query.filter(Analista.activo == activo)

        # Ordenar por ID
        query = query.order_by(Analista.id)

        # Contar total
        total = query.count()

        # Paginar
        analistas = query.limit(limit).all()

        # Calcular páginas
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return AnalistaListResponse(
            items=analistas,
            total=total,
            page=1,
            size=limit,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listando analistas: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/activos", response_model=List[AnalistaResponse])
def listar_analistas_activos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar solo analistas activos"""
    try:
        analistas = db.query(Analista).filter(Analista.activo.is_(True)).all()
        return analistas
    except Exception as e:
        logger.error(f"Error listando analistas activos: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{analista_id}", response_model=AnalistaResponse)
def obtener_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener analista específico
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        return analista

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/", response_model=AnalistaResponse, status_code=status.HTTP_201_CREATED)
def crear_analista(
    analista_data: AnalistaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nuevo analista
    try:
        nuevo_analista = Analista(**analista_data.model_dump())

        db.add(nuevo_analista)
        db.commit()
        db.refresh(nuevo_analista)

        return nuevo_analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{analista_id}", response_model=AnalistaResponse)
def actualizar_analista(
    analista_id: int,
    analista_data: AnalistaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar analista
    try:
        analista = db.query(Analista).filter(Analista.id == analista_id).first()

        if not analista:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        # Actualizar campos
        for field, value in analista_data.model_dump(exclude_unset=True).items():
            setattr(analista, field, value)

        # Actualizar timestamp manually
        analista.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(analista)

        return analista

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando analista: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.delete("/{analista_id}")
def eliminar_analista(
    analista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar analista
    try:
        asesor = db.query(Analista).filter(Analista.id == analista_id).first()

        if not asesor:
            raise HTTPException(status_code=404, detail="Analista no encontrado")

        db.delete(asesor)
        db.commit()
        return {"message": "Analista eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar analista: {str(e)}"
        )
