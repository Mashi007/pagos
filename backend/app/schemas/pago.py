# app/schemas/pago.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class PagoBase(BaseModel):
    prestamo_id: int
    monto_pagado: Decimal = Field(..., gt=0)
    fecha_pago: datetime
    documento_referencia: Optional[str] = None

class PagoCreate(PagoBase):
    pass

class PagoResponse(PagoBase):
    id: int
    numero_cuota: int
    registrado_por: str
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

# ✅ AGREGADO: Schema para lista de pagos
class PagoList(BaseModel):
    """Schema para respuesta paginada de pagos"""
    items: List[PagoResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True
