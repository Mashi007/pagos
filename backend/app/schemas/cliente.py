"""
Schemas Pydantic para Cliente (request/response).
Alineados con la tabla public.clientes en la BD.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ClienteBase(BaseModel):
    cedula: str

    @field_validator("cedula", mode="before")
    @classmethod
    def cedula_empty_default(cls, v: str) -> str:
        """Celda vacía → Z999999999 por defecto."""
        if v is None:
            return "Z999999999"
        s = str(v).strip()
        return s if s else "Z999999999"
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
    """Respuesta de cliente (columnas de la tabla clientes). Tolerante a NULLs en BD."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula: str = ""
    nombres: str = ""
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    fecha_nacimiento: Optional[date] = None
    ocupacion: str = ""
    estado: str = "ACTIVO"
    fecha_registro: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: str = ""
    notas: str = ""
