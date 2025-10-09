# app/schemas/pago.py
"""Schemas para validación de Pago"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class PagoBase(BaseModel):
    """Campos base de Pago"""
    cedula_cliente: str = Field(..., description="Cédula del cliente", min_length=5, max_length=20)
    fecha_programada: date = Field(..., description="Fecha que debió pagar")
    fecha_efectiva: Optional[date] = Field(None, description="Fecha que realmente pagó")
    monto_pagado: float = Field(0, ge=0, description="Monto pagado")
    documento_referencia: Optional[str] = Field(None, max_length=100)
    tipo_pago: Optional[str] = Field(None, max_length=50)
    banco: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None

class PagoCreate(PagoBase):
    """Schema para crear pago"""
    pass

class PagoUpdate(BaseModel):
    """Schema para actualizar pago"""
    fecha_efectiva: Optional[date] = None
    monto_pagado: Optional[float] = Field(None, ge=0)
    documento_referencia: Optional[str] = None
    tipo_pago: Optional[str] = None
    banco: Optional[str] = None
    pagado: Optional[int] = Field(None, ge=0, le=1)
    conciliado: Optional[int] = Field(None, ge=0, le=1)
    observaciones: Optional[str] = None

class PagoResponse(PagoBase):
    """Schema de respuesta de Pago"""
    id: int
    pagado: int
    dias_retraso: int
    conciliado: int
    fecha_conciliacion: Optional[date]
    fecha_registro: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True

class PagoList(BaseModel):
    """Schema para lista de pagos"""
    id: int
    cedula_cliente: str
    fecha_programada: date
    fecha_efectiva: Optional[date]
    monto_pagado: float
    pagado: int
    dias_retraso: int
    
    class Config:
        from_attributes = True
