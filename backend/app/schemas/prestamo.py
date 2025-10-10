# app/schemas/prestamo.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.prestamo import EstadoPrestamo, ModalidadPago

class PrestamoBase(BaseModel):
    cliente_id: int
    monto_total: Decimal = Field(..., gt=0)
    cuotas_totales: int = Field(..., gt=0)
    modalidad: ModalidadPago
    modelo_vehiculo: str = Field(..., min_length=3)
    analista: str = Field(..., min_length=3)
    concesionario: str = Field(..., min_length=3)
    fecha_inicio: datetime

class PrestamoCreate(PrestamoBase):
    pass

class PrestamoUpdate(BaseModel):
    estado: Optional[EstadoPrestamo] = None
    analista: Optional[str] = None
    concesionario: Optional[str] = None

class PrestamoResponse(PrestamoBase):
    id: int
    estado: EstadoPrestamo
    saldo_pendiente: Decimal
    cuotas_pagadas: int
    proxima_fecha_pago: Optional[datetime]
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True

# ✅ AGREGADO: Schema para lista de préstamos
class PrestamoList(BaseModel):
    """Schema para respuesta paginada de préstamos"""
    items: List[PrestamoResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True
