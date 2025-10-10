# backend/app/schemas/cliente.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime


class ClienteBase(BaseModel):
    """Schema base para Cliente"""
    numero_documento: str = Field(..., min_length=8, max_length=20)
    tipo_documento: str = Field(default="DNI", max_length=10)
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Schema para crear un cliente"""
    pass


class ClienteUpdate(BaseModel):
    """Schema para actualizar un cliente (todos los campos opcionales)"""
    numero_documento: Optional[str] = Field(None, min_length=8, max_length=20)
    tipo_documento: Optional[str] = Field(None, max_length=10)
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=20)
    notas: Optional[str] = None


class ClienteResponse(ClienteBase):
    """Schema para respuesta de cliente"""
    id: int
    estado: str
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    usuario_registro: Optional[str] = None

    class Config:
        from_attributes = True  # Reemplazo de orm_mode en Pydantic v2
