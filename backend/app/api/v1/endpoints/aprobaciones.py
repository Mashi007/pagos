from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

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


@router.post(
    "/", response_model=AprobacionResponse, status_code=status.HTTP_201_CREATED
)
def crear_aprobacion(
    aprobacion_data: AprobacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear nueva solicitud de aprobación
    try:
        nueva_aprobacion = Aprobacion(**aprobacion_data.model_dump())
        nueva_aprobacion.solicitado_por = current_user.id

        db.add(nueva_aprobacion)
        db.commit()
        db.refresh(nueva_aprobacion)

        return nueva_aprobacion

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error creando aprobación: {str(e)}"
        )


@router.get("/", response_model=List[AprobacionResponse])
def listar_aprobaciones(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar aprobaciones con filtros
    query = db.query(Aprobacion)

    if estado:
        query = query.filter(Aprobacion.estado == estado)
    if tipo:
        query = query.filter(Aprobacion.tipo == tipo)

    # Si no es admin, solo ver las propias
    if not current_user.is_admin:
        query = query.filter(Aprobacion.solicitado_por == current_user.id)

    return query.all()


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
    if not current_user.is_admin and aprobacion.solicitado_por != current_user.id:
        raise HTTPException(
            status_code=403, detail="No tienes permisos para ver esta aprobación"
        )

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
    if (
        aprobacion.estado != "PENDIENTE"
        and aprobacion.solicitado_por != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="No puedes actualizar esta aprobación"
        )

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
    if not current_user.is_admin:
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
    aprobacion.aprobado_por = current_user.id
    aprobacion.fecha_aprobacion = date.today()
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
    if not current_user.is_admin:
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
    aprobacion.aprobado_por = current_user.id
    aprobacion.fecha_aprobacion = date.today()
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
        raise HTTPException(
            status_code=403, detail="No puedes eliminar esta aprobación"
        )

    db.delete(aprobacion)
    db.commit()

    return {"message": "Aprobación eliminada exitosamente"}
