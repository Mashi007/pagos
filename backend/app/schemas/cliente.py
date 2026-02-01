"""
Schemas Pydantic para Cliente (request/response).
Alineados con la tabla public.clientes en la BD.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    cedula: str
    nombres: str
    telefono: str
    email: str
    direccion: str
    fecha_nacimiento: date
    ocupacion: str
    estado: str = "ACTIVO"
    usuario_registro: str
    notas: str


class ClienteCreate(ClienteBase):
    """Campos para crear cliente."""


class ClienteUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = None
    estado: Optional[str] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None


class ClienteResponse(BaseModel):
    """Respuesta de cliente (columnas de la tabla clientes)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula: str
    nombres: str
    telefono: str
    email: str
    direccion: str
    fecha_nacimiento: date
    ocupacion: str
    estado: str
    fecha_registro: datetime
    fecha_actualizacion: datetime
    usuario_registro: str
    notas: str
