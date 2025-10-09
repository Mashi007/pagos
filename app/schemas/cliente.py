# app/schemas/cliente.py
"""Schemas para validación de Cliente"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import date, datetime

class ClienteBase(BaseModel):
    """Campos base de Cliente"""
    cedula: str = Field(..., description="Cédula de identidad", min_length=5, max_length=20)
    nombre: str = Field(..., description="Nombre completo", min_length=3, max_length=200)
    movil: Optional[str] = Field(None, max_length=20)
    whatsapp: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    estado_caso: Optional[str] = Field("ACTIVO", max_length=50)
    modelo_vehiculo: Optional[str] = Field(None, max_length=100)
    analista: Optional[str] = Field(None, max_length=100)
    concesionario: Optional[str] = Field(None, max_length=100)
    fecha_pago_inicial: Optional[date] = None
    fecha_entrega_vehiculo: Optional[date] = None
    total_financiado: Optional[float] = Field(None, ge=0)
    cuota_inicial: Optional[float] = Field(None, ge=0)
    numero_cuotas: Optional[int] = Field(None, ge=1)
    modalidad_financiamiento: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None

class ClienteCreate(ClienteBase):
    """Schema para crear cliente"""
    pass

class ClienteUpdate(BaseModel):
    """Schema para actualizar cliente (todos los campos opcionales)"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    movil: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    estado_caso: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    analista: Optional[str] = None
    concesionario: Optional[str] = None
    fecha_pago_inicial: Optional[date] = None
    fecha_entrega_vehiculo: Optional[date] = None
    total_financiado: Optional[float] = Field(None, ge=0)
    cuota_inicial: Optional[float] = Field(None, ge=0)
    numero_cuotas: Optional[int] = Field(None, ge=1)
    modalidad_financiamiento: Optional[str] = None
    observaciones: Optional[str] = None
    requiere_actualizacion: Optional[int] = Field(None, ge=0, le=1)

class ClienteResponse(ClienteBase):
    """Schema de respuesta de Cliente"""
    requiere_actualizacion: int
    fecha_registro: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True

class ClienteList(BaseModel):
    """Schema para lista de clientes"""
    cedula: str
    nombre: str
    movil: Optional[str]
    estado_caso: Optional[str]
    modelo_vehiculo: Optional[str]
    total_financiado: Optional[float]
    
    class Config:
        from_attributes = True
