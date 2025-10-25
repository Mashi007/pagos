from datetime import date
# backend/app/schemas/prestamo.py

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constantes de validación
MAX_PERCENTAGE = 100
DECIMAL_PRECISION = 2
MIN_PASSWORD_LENGTH = 8

DecimalAmount = Annotated[
    Decimal,
    Field(ge=0, description="Monto en formato decimal con 2 decimales"),
]

DecimalPercentage = Annotated[
    Decimal,
    Field(ge=0, le=MAX_PERCENTAGE, description="Porcentaje con 2 decimales"),
]


class PrestamoBase(BaseModel):
    """Schema base para Préstamo"""
    cliente_id: int
    monto_total: Decimal = Field
    )
    monto_financiado: Decimal = Field
    )
    monto_inicial: Decimal = Field
        default=Decimal("0.00"),
        ge=0,
        description="Monto inicial/cuota inicial",
    )
    tasa_interes: Decimal = Field
        default=Decimal("0.00"),
        ge=0,
        le=MAX_PERCENTAGE,
        description="Tasa de interés anual (%)",
    )
    numero_cuotas: int = Field(..., gt=0, description="Número de cuotas")
    monto_cuota: Decimal = Field(..., gt=0, description="Monto de cada cuota")
    fecha_aprobacion: date
    fecha_desembolso: Optional[date] = None
    fecha_primer_vencimiento: date
    fecha_ultimo_vencimiento: Optional[date] = None
    modalidad: str = Field
    )
    destino_credito: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator
    )
    @classmethod
    def validate_decimal_places(cls, v):
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PrestamoCreate(PrestamoBase):
    """Schema para crear un préstamo"""
    pass


class PrestamoUpdate(BaseModel):
    """Schema para actualizar un préstamo"""
    monto_total: Optional[Decimal] = Field
    )
    tasa_interes: Optional[Decimal] = Field
        None, ge=0, le=MAX_PERCENTAGE, description="Tasa de interés anual (%)"
    )
    estado: Optional[str] = None
    categoria: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("monto_total", "tasa_interes", mode="before")
    @classmethod
    def validate_decimal_places(cls, v):
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    model_config = ConfigDict(from_attributes=True)

    @field_validator
    )
    @classmethod
    def validate_decimal_places(cls, v):
        if v is None:
            return Decimal("0.00")
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
