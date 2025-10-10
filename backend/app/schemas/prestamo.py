# backend/app/schemas/prestamo.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


class PrestamoBase(BaseModel):
    """Schema base para Préstamo"""
    cliente_id: int
    monto_total: Decimal = Field(..., gt=0, decimal_places=2, description="Monto total del préstamo")
    monto_financiado: Decimal = Field(..., gt=0, decimal_places=2, description="Monto financiado")
    monto_inicial: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="Monto inicial/cuota inicial")
    tasa_interes: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, decimal_places=2, description="Tasa de interés anual (%)")
    numero_cuotas: int = Field(..., gt=0, description="Número de cuotas")
    monto_cuota: Decimal = Field(..., gt=0, decimal_places=2, description="Monto de cada cuota")
    fecha_aprobacion: date
    fecha_desembolso: Optional[date] = None
    fecha_primer_vencimiento: date
    fecha_ultimo_vencimiento: Optional[date] = None
    modalidad: str = Field(default="MENSUAL")  # SEMANAL, QUINCENAL, MENSUAL
    destino_credito: Optional[str] = None
    observaciones: Optional[str] = None
    
    @field_validator('monto_total', 'monto_financiado', 'monto_inicial', 'monto_cuota', mode='before')
    @classmethod
    def validate_decimal_places(cls, v) -> Decimal:
        """Validar que los montos tengan máximo 2 decimales"""
        if v is None:
            return v
        # Convertir a Decimal si no lo es
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        # Redondear a 2 decimales
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @field_validator('tasa_interes', mode='before')
    @classmethod
    def validate_tasa_interes(cls, v) -> Decimal:
        """Validar que la tasa de interés tenga máximo 2 decimales"""
        if v is None:
            return v
        # Convertir a Decimal si no lo es
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        # Redondear a 2 decimales
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PrestamoCreate(PrestamoBase):
    """Schema para crear un préstamo"""
    pass


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""
    monto_total: Optional[Decimal] = Field(None, gt=0, decimal_places=2, description="Monto total del préstamo")
    tasa_interes: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2, description="Tasa de interés anual (%)")
    estado: Optional[str] = None
    categoria: Optional[str] = None
    observaciones: Optional[str] = None
    
    @field_validator('monto_total', mode='before')
    @classmethod
    def validate_monto_total(cls, v) -> Optional[Decimal]:
        """Validar que el monto total tenga máximo 2 decimales"""
        if v is None:
            return v
        # Convertir a Decimal si no lo es
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @field_validator('tasa_interes', mode='before')
    @classmethod
    def validate_tasa_interes(cls, v) -> Optional[Decimal]:
        """Validar que la tasa de interés tenga máximo 2 decimales"""
        if v is None:
            return v
        # Convertir a Decimal si no lo es
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class PrestamoResponse(PrestamoBase):
    """Schema para respuesta de préstamo"""
    id: int
    codigo_prestamo: Optional[str] = None
    saldo_pendiente: Decimal = Field(decimal_places=2)
    saldo_capital: Decimal = Field(decimal_places=2)
    saldo_interes: Decimal = Field(decimal_places=2)
    total_pagado: Decimal = Field(decimal_places=2)
    estado: str
    categoria: str
    cuotas_pagadas: int
    cuotas_pendientes: Optional[int] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
