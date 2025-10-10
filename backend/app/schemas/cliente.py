# backend/app/schemas/cliente.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime


class ClienteBase(BaseModel):
    cedula: str = Field(..., min_length=8, max_length=20)
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    cedula: Optional[str] = Field(None, min_length=8, max_length=20)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = None
    notas: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: int
    estado: str
    activo: bool
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: Optional[str] = None

    class Config:
        from_attributes = True
