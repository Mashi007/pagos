# backend/app/schemas/pago.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal


class PagoBase(BaseModel):
    """Schema base para Pago"""
    prestamo_id: int
    monto_pagado: Decimal = Field(..., gt=0, decimal_places=2)
    monto_capital: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    monto_interes: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    monto_mora: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    fecha_pago: date
    fecha_vencimiento: date
    metodo_pago: str = Field(default="EFECTIVO")
    numero_operacion: Optional[str] = Field(None, max_length=50)
    comprobante: Optional[str] = Field(None, max_length=50)
    banco: Optional[str] = Field(None, max_length=50)
    observaciones: Optional[str] = None


class PagoCreate(PagoBase):
    """Schema para crear un pago"""
    pass


class PagoResponse(PagoBase):
    """Schema para respuesta de pago"""
    id: int
    numero_cuota: int
    codigo_pago: Optional[str] = None
    monto_cuota_programado: Decimal
    monto_total: Decimal
    hora_pago: Optional[time] = None
    dias_mora: int
    tasa_mora: Decimal
    estado: str
    tipo_pago: str
    usuario_registro: Optional[str] = None
    creado_en: datetime

    class Config:
        from_attributes = True
