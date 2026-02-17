"""
Schemas Pydantic para Préstamo (request/response).
Alineados con la tabla public.prestamos en la BD (columnas confirmadas).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PrestamoBase(BaseModel):
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: str = ""
    modalidad_pago: Optional[str] = None  # MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas: Optional[int] = None
    fecha_requerimiento: Optional[date] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    """Campos para crear préstamo. cedula/nombres se rellenan desde Cliente si no se envían."""


class PrestamoUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cliente_id: Optional[int] = None
    total_financiamiento: Optional[Decimal] = None
    estado: Optional[str] = None
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    fecha_requerimiento: Optional[date] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoResponse(BaseModel):
    """Respuesta de préstamo (columnas de la tabla prestamos)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    fecha_registro: Optional[datetime] = None
    fecha_aprobacion: Optional[datetime] = None
    # Campos para detalle (cedula/nombres en prestamos; cuota_periodo, etc.)
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    cuota_periodo: Optional[Decimal] = None
    fecha_requerimiento: Optional[date] = None
    tasa_interes: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoListResponse(PrestamoResponse):
    """Préstamo para listado: incluye nombres y cedula del cliente (join)."""
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    numero_cuotas: Optional[int] = None
    modalidad_pago: Optional[str] = None
