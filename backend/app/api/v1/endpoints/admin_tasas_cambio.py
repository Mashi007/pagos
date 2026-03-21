"""
Endpoints para administrar tasas de cambio oficial (admin).
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_utils import user_is_administrator
from app.schemas.auth import UserResponse
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.services.tasa_cambio_service import (
    obtener_tasa_hoy,
    obtener_tasa_por_fecha,
    guardar_tasa_diaria,
    debe_ingresar_tasa,
)

router = APIRouter(prefix="/admin/tasas-cambio", tags=["admin-tasas-cambio"])


class TasaCambioResponse(BaseModel):
    id: int
    fecha: date
    tasa_oficial: float
    usuario_email: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class GuardarTasaRequest(BaseModel):
    tasa_oficial: float = Field(..., gt=0, description="Tasa oficial BS/USD, ej: 2850.50")


@router.get("/hoy", response_model=Optional[TasaCambioResponse])
def get_tasa_hoy(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene la tasa de cambio para hoy."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    tasa = obtener_tasa_hoy(db)
    return tasa


@router.get("/estado")
def get_estado_tasa(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Verifica si es necesario ingresar la tasa y devuelve el estado."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    debe_ingresar = debe_ingresar_tasa()
    tasa_guardada = obtener_tasa_hoy(db)
    
    return {
        "debe_ingresar": debe_ingresar,
        "tasa_ya_ingresada": tasa_guardada is not None,
        "hora_obligatoria_desde": "01:00",
        "hora_obligatoria_hasta": "23:59",
    }


@router.post("/guardar", response_model=TasaCambioResponse)
def guardar_tasa(
    req: GuardarTasaRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Guarda la tasa de cambio oficial para hoy. Obligatorio desde 01:00 AM."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    if not debe_ingresar_tasa():
        raise HTTPException(
            status_code=400,
            detail="La tasa solo se puede ingresar desde las 01:00 AM hasta las 23:59 PM"
        )
    
    usuario_email = current_user.email
    usuario_id = current_user.id
    
    tasa = guardar_tasa_diaria(
        db=db,
        tasa_oficial=req.tasa_oficial,
        usuario_id=usuario_id,
        usuario_email=usuario_email,
    )
    
    return tasa


@router.get("/por-fecha", response_model=Optional[TasaCambioResponse])
def get_tasa_por_fecha(
    fecha: date = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene la tasa de cambio para una fecha específica."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    tasa = obtener_tasa_por_fecha(db, fecha)
    return tasa


@router.get("/historial")
def get_historial_tasas(
    limite: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtiene el historial de tasas (últimas N fechas)."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    from sqlalchemy import desc
    tasas = db.query(TasaCambioDiaria).order_by(desc(TasaCambioDiaria.fecha)).limit(limite).all()
    
    return [
        {
            "id": t.id,
            "fecha": t.fecha.isoformat(),
            "tasa_oficial": float(t.tasa_oficial),
            "usuario_email": t.usuario_email,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in tasas
    ]

