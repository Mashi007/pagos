"""Endpoints de Aprobaciones
Sistema de workflow para solicitudes que requieren aprobación
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.constants import EstadoAprobacion
from app.models.aprobacion import Aprobacion
from app.models.user import User

router = APIRouter()

# ============================================
# SCHEMAS PYDANTIC
# ============================================

class AprobacionCreate(BaseModel):
    tipo_solicitud: str
    nivel: Optional[str] = None
    entidad: str
    entidad_id: int
    justificacion: str
    datos_solicitados: Optional[str] = None

class AprobacionUpdate(BaseModel):
    estado: str
    comentarios_revisor: Optional[str] = None

class AprobacionResponse(BaseModel):
    id: int
    estado: str
    tipo_solicitud: str
    nivel: Optional[str]
    entidad: str
    entidad_id: int
    justificacion: str
    comentarios_revisor: Optional[str]
    fecha_solicitud: datetime
    fecha_revision: Optional[datetime]
    solicitante_id: int
    revisor_id: Optional[int]

    class Config:
        from_attributes = True

# ============================================
# ENDPOINTS
# ============================================

@router.post(
    "/", response_model=AprobacionResponse, status_code=status.HTTP_201_CREATED
)
def crear_aprobacion(
    aprobacion_data: AprobacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear nueva solicitud de aprobación"""
    aprobacion = Aprobacion(
        solicitante_id=current_user.id,
        estado=EstadoAprobacion.PENDIENTE.value,
        tipo_solicitud=aprobacion_data.tipo_solicitud,
        nivel=aprobacion_data.nivel,
        entidad=aprobacion_data.entidad,
        entidad_id=aprobacion_data.entidad_id,
        justificacion=aprobacion_data.justificacion,
        datos_solicitados=aprobacion_data.datos_solicitados,
    )
    db.add(aprobacion)
    db.commit()
    db.refresh(aprobacion)
    return aprobacion

@router.get("/", response_model=List[AprobacionResponse])
def listar_aprobaciones(
    estado: Optional[str] = None,
    tipo_solicitud: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar aprobaciones con filtros"""
    query = db.query(Aprobacion)
    if estado:
        query = query.filter(Aprobacion.estado == estado)
    if tipo_solicitud:
        query = query.filter(Aprobacion.tipo_solicitud == tipo_solicitud)
    aprobaciones = query.offset(skip).limit(limit).all()
    return aprobaciones

@router.get("/{aprobacion_id}", response_model=AprobacionResponse)
def obtener_aprobacion(
    aprobacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener aprobación por ID"""
    aprobacion = (
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()
    )
    if not aprobacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aprobación no encontrada",
        )
    return aprobacion

@router.put("/{aprobacion_id}", response_model=AprobacionResponse)
def actualizar_aprobacion(
    aprobacion_id: int,
    aprobacion_update: AprobacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aprobar o rechazar una solicitud"""
    aprobacion = (
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()
    )
    if not aprobacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aprobación no encontrada",
        )
    if not aprobacion.esta_pendiente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta aprobación ya fue procesada",
        )
    # Actualizar según el estado
    if aprobacion_update.estado == EstadoAprobacion.APROBADA.value:
        aprobacion.aprobar(
            current_user.id, aprobacion_update.comentarios_revisor
        )
    elif aprobacion_update.estado == EstadoAprobacion.RECHAZADA.value:
        if not aprobacion_update.comentarios_revisor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Los comentarios son obligatorios al rechazar",
            )
        aprobacion.rechazar(
            current_user.id, aprobacion_update.comentarios_revisor
        )
    elif aprobacion_update.estado == EstadoAprobacion.CANCELADA.value:
        aprobacion.cancelar()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Estado no válido"
        )
    db.commit()
    db.refresh(aprobacion)
    return aprobacion

@router.delete("/{aprobacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_aprobacion(
    aprobacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar una solicitud de aprobación"""
    aprobacion = (
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first()
    )
    if not aprobacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aprobación no encontrada",
        )
    # Solo el solicitante puede eliminar su propia solicitud pendiente
    if (
        aprobacion.solicitante_id != current_user.id
        or not aprobacion.esta_pendiente
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta aprobación",
        )
    db.delete(aprobacion)
    db.commit()
    return None