# app/schemas/cliente.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    cedula: str = Field(..., min_length=5, max_length=20)
    telefono: str = Field(..., min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    telefono: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = None
    activo: Optional[bool] = None

class ClienteResponse(ClienteBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True
