"""
Schemas Pydantic para Cliente (request/response).
Alineados con el frontend (Cliente, ClienteForm).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ClienteBase(BaseModel):
    cedula: str
    nombres: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    total_financiamiento: Optional[Decimal] = None
    cuota_inicial: Optional[Decimal] = None
    monto_financiado: Optional[Decimal] = None
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = None
    modalidad_pago: Optional[str] = None
    estado: str = "ACTIVO"
    activo: bool = True
    estado_financiero: Optional[str] = None
    dias_mora: int = 0
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Campos para crear cliente (ClienteForm del frontend)."""
    estado: str = "ACTIVO"
    activo: bool = True
    dias_mora: int = 0


class ClienteUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    total_financiamiento: Optional[Decimal] = None
    cuota_inicial: Optional[Decimal] = None
    monto_financiado: Optional[Decimal] = None
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = None
    modalidad_pago: Optional[str] = None
    estado: Optional[str] = None
    activo: Optional[bool] = None
    estado_financiero: Optional[str] = None
    dias_mora: Optional[int] = None
    notas: Optional[str] = None


class ClienteResponse(BaseModel):
    """Respuesta de cliente (formato esperado por el frontend)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula: str
    nombres: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    total_financiamiento: Optional[float] = None
    cuota_inicial: Optional[float] = None
    monto_financiado: Optional[float] = None
    fecha_entrega: Optional[date] = None
    numero_amortizaciones: Optional[int] = None
    modalidad_pago: Optional[str] = None
    estado: str
    activo: bool
    estado_financiero: Optional[str] = None
    dias_mora: int
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None
