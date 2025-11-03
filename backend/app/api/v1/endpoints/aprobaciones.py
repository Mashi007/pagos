import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user, get_db
from app.models.aprobacion import Aprobacion
from app.models.user import User
from app.schemas.aprobacion import (
    AprobacionCreate,
    AprobacionResponse,
    AprobacionUpdate,
)

# Endpoints de Aprobaciones
# Sistema de workflow para solicitudes que requieren aprobación


router = APIRouter()


@router.post("/", response_model=AprobacionResponse, status_code=status.HTTP_201_CREATED)
def crear_aprobacion(
    aprobacion_data: AprobacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nueva solicitud de aprobación
    try:
        nueva_aprobacion = Aprobacion(**aprobacion_data.model_dump())
        nueva_aprobacion.solicitado_por = int(current_user.id)

        db.add(nueva_aprobacion)
        db.commit()
        db.refresh(nueva_aprobacion)

        return nueva_aprobacion

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando aprobación: {str(e)}")


@router.get("/")
def listar_aprobaciones(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Registros por página"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar aprobaciones con filtros y paginación
    """
    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    try:
        # Calcular paginación
        skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

        # Query base
        query = db.query(Aprobacion)

        if estado:
            query = query.filter(Aprobacion.estado == estado)
        if tipo:
            query = query.filter(Aprobacion.tipo == tipo)

        # Si no es admin, solo ver las propias
        if not bool(current_user.is_admin):
            query = query.filter(Aprobacion.solicitado_por == current_user.id)

        # Contar total
        total = query.count()

        # Aplicar paginación con ordenamiento
        aprobaciones = query.order_by(Aprobacion.created_at.desc()).offset(skip).limit(limit).all()

        # Retornar respuesta paginada
        return create_paginated_response(items=aprobaciones, total=total, page=page, page_size=limit)

    except Exception as e:
        logger.error(f"Error listando aprobaciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{aprobacion_id}", response_model=AprobacionResponse)
def obtener_aprobacion(
    aprobacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener aprobación específica
    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()

    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    # Verificar permisos
    if not bool(current_user.is_admin) and aprobacion.solicitado_por != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta aprobación")

    return aprobacion


@router.put("/{aprobacion_id}", response_model=AprobacionResponse)
def actualizar_aprobacion(
    aprobacion_id: int,
    aprobacion_data: AprobacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar aprobación
    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()

    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    # Solo el solicitante puede actualizar si está pendiente
    if aprobacion.estado != "PENDIENTE" and aprobacion.solicitado_por != int(current_user.id):
        raise HTTPException(status_code=403, detail="No puedes actualizar esta aprobación")

    # Actualizar campos
    for field, value in aprobacion_data.model_dump(exclude_unset=True).items():
        setattr(aprobacion, field, value)

    db.commit()
    db.refresh(aprobacion)

    return aprobacion


@router.post("/{aprobacion_id}/aprobar", response_model=AprobacionResponse)
def aprobar_solicitud(
    aprobacion_id: int,
    observaciones: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Aprobar solicitud (solo admins)
    if not bool(current_user.is_admin):
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden aprobar solicitudes",
        )

    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()

    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    if aprobacion.estado != "PENDIENTE":
        raise HTTPException(status_code=400, detail="Esta solicitud ya fue procesada")

    aprobacion.estado = "APROBADA"
    aprobacion.aprobado_por = int(current_user.id)
    aprobacion.fecha_aprobacion = datetime.now()
    aprobacion.observaciones_aprobacion = observaciones

    db.commit()
    db.refresh(aprobacion)

    return aprobacion


@router.post("/{aprobacion_id}/rechazar", response_model=AprobacionResponse)
def rechazar_solicitud(
    aprobacion_id: int,
    observaciones: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rechazar solicitud (solo admins)
    if not bool(current_user.is_admin):
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden rechazar solicitudes",
        )

    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()

    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    if aprobacion.estado != "PENDIENTE":
        raise HTTPException(status_code=400, detail="Esta solicitud ya fue procesada")

    aprobacion.estado = "RECHAZADA"
    aprobacion.aprobado_por = int(current_user.id)
    aprobacion.fecha_aprobacion = datetime.now()
    aprobacion.observaciones_aprobacion = observaciones

    db.commit()
    db.refresh(aprobacion)

    return aprobacion


@router.delete("/{aprobacion_id}")
def eliminar_aprobacion(
    aprobacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar aprobación
    aprobacion = db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()

    if not aprobacion:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    # Solo el solicitante puede eliminar si está pendiente
    if aprobacion.estado != "PENDIENTE" or aprobacion.solicitado_por != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar esta aprobación")

    db.delete(aprobacion)
    db.commit()

    return {"message": "Aprobación eliminada exitosamente"}
