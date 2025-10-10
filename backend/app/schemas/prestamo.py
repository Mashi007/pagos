# backend/app/schemas/prestamo.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class PrestamoBase(BaseModel):
    """Schema base para Préstamo"""
    cliente_id: int
    monto_total: Decimal = Field(..., gt=0, decimal_places=2)
    monto_financiado: Decimal = Field(..., gt=0, decimal_places=2)
    monto_inicial: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    tasa_interes: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    numero_cuotas: int = Field(..., gt=0)
    monto_cuota: Decimal = Field(..., gt=0, decimal_places=2)
    fecha_aprobacion: date
    fecha_desembolso: Optional[date] = None
    fecha_primer_vencimiento: date
    fecha_ultimo_vencimiento: Optional[date] = None
    modalidad: str = Field(default="MENSUAL")  # SEMANAL, QUINCENAL, MENSUAL
    destino_credito: Optional[str] = None
    observaciones: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    """Schema para crear un préstamo"""
    pass


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""
    monto_total: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    tasa_interes: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    estado: Optional[str] = None
    categoria: Optional[str] = None
    observaciones: Optional[str] = None


class PrestamoResponse(PrestamoBase):
    """Schema para respuesta de préstamo"""
    id: int
    codigo_prestamo: Optional[str] = None
    saldo_pendiente: Decimal
    saldo_capital: Decimal
    saldo_interes: Decimal
    total_pagado: Decimal
    estado: str
    categoria: str
    cuotas_pagadas: int
    cuotas_pendientes: Optional[int] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None

    class Config:
        from_attributes = True
