"""
Endpoints para administrar tasas de cambio oficial (admin).
"""
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_utils import user_is_administrator
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.tasa_cambio_service import (
    obtener_tasa_hoy,
    obtener_tasa_por_fecha,
    guardar_tasa_diaria,
    guardar_tasa_para_fecha,
    debe_ingresar_tasa,
)

router = APIRouter(prefix="/admin/tasas-cambio", tags=["admin-tasas-cambio"])


class TasaCambioResponse(BaseModel):
    """Respuesta API: fechas como string ISO (el ORM entrega datetime)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    tasa_oficial: float
    usuario_email: Optional[str] = None
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def coerce_datetime_to_iso(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, str):
            return v
        raise ValueError("created_at/updated_at must be datetime or str")


class GuardarTasaRequest(BaseModel):
    tasa_oficial: float = Field(..., gt=0, description="Tasa oficial BS/USD, ej: 2850.50")


class GuardarTasaPorFechaRequest(BaseModel):
    """Backfill: tasa para una fecha de pago (no aplica ventana 01:00 de guardar/hoy)."""

    fecha: date = Field(..., description="Fecha calendario YYYY-MM-DD (fecha_pago del reporte)")
    tasa_oficial: float = Field(..., gt=0, description="Bs. por 1 USD")


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
            detail="La tasa solo se puede ingresar desde las 01:00 AM hasta las 23:59 PM",
        )

    db_user = db.query(User).filter(User.email == current_user.email).first()
    usuario_id = db_user.id if db_user else None
    usuario_email = current_user.email

    tasa = guardar_tasa_diaria(
        db=db,
        tasa_oficial=req.tasa_oficial,
        usuario_id=usuario_id,
        usuario_email=usuario_email,
    )

    return tasa


@router.post("/guardar-por-fecha", response_model=TasaCambioResponse)
def guardar_tasa_por_fecha_endpoint(
    req: GuardarTasaPorFechaRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Inserta o actualiza la tasa oficial para una fecha arbitraria.
    Administradores: útil para registrar tasas faltantes al corregir pagos BS históricos.
    """
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    db_user = db.query(User).filter(User.email == current_user.email).first()
    usuario_id = db_user.id if db_user else None
    usuario_email = current_user.email

    tasa = guardar_tasa_para_fecha(
        db=db,
        fecha=req.fecha,
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
    """Obtiene la tasa de cambio para una fecha especifica."""
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
    """Obtiene el historial de tasas (ultimas N fechas)."""
    if not user_is_administrator(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores")

    from sqlalchemy import desc

    tasas = (
        db.query(TasaCambioDiaria)
        .order_by(desc(TasaCambioDiaria.fecha))
        .limit(limite)
        .all()
    )

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
