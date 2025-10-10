# app/schemas/prestamo.py

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from app.models.prestamo import EstadoPrestamo, ModalidadPago


class PrestamoBase(BaseModel):
    """Schema base para préstamos"""
    cliente_id: int = Field(..., gt=0, description="ID del cliente")
    monto_total: Decimal = Field(..., gt=0, description="Monto total del préstamo")
    monto_financiado: Decimal = Field(..., gt=0, description="Monto financiado")
    monto_inicial: Decimal = Field(default=0.00, ge=0, description="Monto inicial/cuota inicial")
    tasa_interes: Decimal = Field(default=0.00, ge=0, le=100, description="Tasa de interés anual")
    numero_cuotas: int = Field(..., gt=0, description="Número total de cuotas")
    monto_cuota: Decimal = Field(..., gt=0, description="Monto de cada cuota")
    fecha_aprobacion: date = Field(..., description="Fecha de aprobación del préstamo")
    fecha_primer_vencimiento: date = Field(..., description="Fecha del primer vencimiento")
    modalidad: ModalidadPago = Field(default=ModalidadPago.TRADICIONAL, description="Modalidad de pago")
    destino_credito: Optional[str] = Field(None, description="Destino del crédito")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales")


class PrestamoCreate(PrestamoBase):
    """Schema para crear un préstamo"""
    pass


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""
    estado: Optional[EstadoPrestamo] = None
    categoria: Optional[str] = None
    modalidad: Optional[ModalidadPago] = None
    observaciones: Optional[str] = None
    saldo_pendiente: Optional[Decimal] = None
    cuotas_pagadas: Optional[int] = None


class PrestamoResponse(BaseModel):
    """Schema de respuesta para préstamo"""
    id: int
    cliente_id: int
    codigo_prestamo: Optional[str]
    
    # Montos
    monto_total: Decimal
    monto_financiado: Decimal
    monto_inicial: Decimal
    tasa_interes: Decimal
    
    # Cuotas
    numero_cuotas: int
    monto_cuota: Decimal
    cuotas_pagadas: int
    cuotas_pendientes: Optional[int]
    
    # Fechas
    fecha_aprobacion: date
    fecha_desembolso: Optional[date]
    fecha_primer_vencimiento: date
    fecha_ultimo_vencimiento: Optional[date]
    
    # Estado financiero
    saldo_pendiente: Decimal
    saldo_capital: Decimal
    saldo_interes: Decimal
    total_pagado: Decimal
    
    # Estado
    estado: str
    categoria: str
    modalidad: str
    
    # Información adicional
    destino_credito: Optional[str]
    observaciones: Optional[str]
    
    # Auditoría
    creado_en: datetime
    actualizado_en: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PrestamoList(BaseModel):
    """Schema para respuesta paginada de préstamos"""
    items: List[PrestamoResponse]
    total: int
    page: int
    size: int
    pages: int
