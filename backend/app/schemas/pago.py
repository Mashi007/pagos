# backend/app/schemas/pago.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal, ROUND_HALF_UP


class PagoBase(BaseModel):
    """Schema base para Pago"""
    prestamo_id: int
    monto_pagado: Decimal = Field(..., gt=0, description="Monto pagado")
    monto_capital: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto aplicado a capital")
    monto_interes: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto aplicado a interés")
    monto_mora: Decimal = Field(default=Decimal("0.00"), ge=0, description="Monto de mora")
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0, description="Descuento aplicado")
    fecha_pago: date
    fecha_vencimiento: date
    metodo_pago: str = Field(default="EFECTIVO")
    numero_operacion: Optional[str] = Field(None, max_length=50)
    comprobante: Optional[str] = Field(None, max_length=50)
    banco: Optional[str] = Field(None, max_length=50)
    observaciones: Optional[str] = None
    
    @field_validator('monto_pagado', 'monto_capital', 'monto_interes', 'monto_mora', 'descuento', mode='before')
    @classmethod
    def validate_decimal_places(cls, v: Decimal) -> Decimal:
        """Validar que los montos tengan máximo 2 decimales"""
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        # Redondear a 2 decimales
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


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
    
    model_config = ConfigDict(from_attributes=True)


class PagoList(BaseModel):
    """Schema para lista de pagos con paginación"""
    items: list[PagoResponse]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int
    
    model_config = ConfigDict(from_attributes=True)
