"""
Schemas Pydantic para Préstamo (request/response).
Alineados con la tabla public.prestamos en la BD.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PrestamoBase(BaseModel):
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "PENDIENTE"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    """Campos para crear préstamo."""


class PrestamoUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cliente_id: Optional[int] = None
    total_financiamiento: Optional[Decimal] = None
    estado: Optional[str] = None
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None


class PrestamoResponse(BaseModel):
    """Respuesta de préstamo (columnas de la tabla prestamos)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "PENDIENTE"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
