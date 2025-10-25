from datetime import date
"""Endpoints de Aprobaciones
Sistema de workflow para solicitudes que requieren aprobación
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.constants import EstadoAprobacion
from app.models.aprobacion import Aprobacion
from app.models.user import User

router = APIRouter(
# ============================================
# SCHEMAS PYDANTIC
# ============================================


class AprobacionCreate(BaseModel):
    tipo_solicitud: str
    nivel: Optional[str] = None
    entidad: str
    entidad_id: int
    justificacion: str


class AprobacionUpdate(BaseModel):
    estado: str


class AprobacionResponse(BaseModel):
    id: int
    estado: str
    tipo_solicitud: str
    nivel: Optional[str]
    entidad: str
    entidad_id: int
    justificacion: str
    solicitante_id: int
    revisor_id: Optional[int]


    class Config:
        from_attributes = True

# ============================================
# ENDPOINTS
# ============================================

    "/", response_model=AprobacionResponse, status_code=status.HTTP_201_CREATED

def crear_aprobacion
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """Crear nueva solicitud de aprobación"""
    aprobacion = Aprobacion
    
    db.add(aprobacion
    db.commit(
    db.refresh(aprobacion
    return aprobacion

@router.get("/", response_model=List[AprobacionResponse]
def listar_aprobaciones
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    query = db.query(Aprobacion
    if estado:
        query = query.filter(Aprobacion.estado == estado
    if tipo_solicitud:
        query = query.filter(Aprobacion.tipo_solicitud == tipo_solicitud
    aprobaciones = query.offset(skip).limit(limit).all(
    return aprobaciones

@router.get("/{aprobacion_id}", response_model=AprobacionResponse
def obtener_aprobacion
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """Obtener aprobación por ID"""
    aprobacion = 
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first(
    
    if not aprobacion:
        raise HTTPException
        
    return aprobacion

@router.put("/{aprobacion_id}", response_model=AprobacionResponse
def actualizar_aprobacion
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """Aprobar o rechazar una solicitud"""
    aprobacion = 
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first(
    
    if not aprobacion:
        raise HTTPException
        
    if not aprobacion.esta_pendiente:
        raise HTTPException
        
    # Actualizar según el estado
    if aprobacion_update.estado == EstadoAprobacion.APROBADA.value:
        aprobacion.aprobar
        
    elif aprobacion_update.estado == EstadoAprobacion.RECHAZADA.value:
            raise HTTPException
            
        aprobacion.rechazar
        
    elif aprobacion_update.estado == EstadoAprobacion.CANCELADA.value:
        aprobacion.cancelar(
    else:
        raise HTTPException
        
    db.commit(
    db.refresh(aprobacion
    return aprobacion

@router.delete("/{aprobacion_id}", status_code=status.HTTP_204_NO_CONTENT
def eliminar_aprobacion
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    """Eliminar una solicitud de aprobación"""
    aprobacion = 
        db.query(Aprobacion).filter(Aprobacion.id == aprobacion_id).first(
    
    if not aprobacion:
        raise HTTPException
        
    # Solo el solicitante puede eliminar su propia solicitud pendiente
    if 
        raise HTTPException
        
    db.delete(aprobacion
    db.commit(
    return None
