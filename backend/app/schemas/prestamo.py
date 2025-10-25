from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Constantes
MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000.00")
MAX_PERCENTAGE = 100
DECIMAL_PRECISION = 2
MIN_PASSWORD_LENGTH = 8

DecimalAmount = Decimal
DecimalPercentage = Decimal


class PrestamoBase(BaseModel):
    # Schema base para Préstamo
    cliente_id: int
    monto_total: Decimal = Field(..., ge=0, description="Monto total del préstamo")
    monto_financiado: Decimal = Field(..., ge=0, description="Monto financiado")
    monto_inicial: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Monto inicial pagado"
    )
    tasa_interes: Decimal = Field(
        ..., ge=0, le=100, description="Tasa de interés anual (%)"
    )
    numero_cuotas: int = Field(..., gt=0, description="Número de cuotas")
    fecha_inicio: date = Field(..., description="Fecha de inicio del préstamo")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    estado: str = Field(default="ACTIVO", description="Estado del préstamo")
    observaciones: Optional[str] = Field(None, description="Observaciones")

    @field_validator("monto_total", "monto_financiado", "monto_inicial", "tasa_interes")
    @classmethod
    def validate_decimal_places(cls, v):
        if isinstance(v, Decimal):
            return v.quantize(Decimal("0.01"))
        return Decimal(str(v)).quantize(Decimal("0.01"))


class PrestamoCreate(PrestamoBase):
    # Schema para crear préstamo
    pass


class PrestamoUpdate(BaseModel):
    # Schema para actualizar préstamo
    monto_total: Optional[Decimal] = Field(None, ge=0)
    monto_financiado: Optional[Decimal] = Field(None, ge=0)
    monto_inicial: Optional[Decimal] = Field(None, ge=0)
    tasa_interes: Optional[Decimal] = Field(None, ge=0, le=100)
    numero_cuotas: Optional[int] = Field(None, gt=0)
    fecha_inicio: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("monto_total", "monto_financiado", "monto_inicial", "tasa_interes")
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None and isinstance(v, Decimal):
            return v.quantize(Decimal("0.01"))
        return v


class PrestamoResponse(PrestamoBase):
    # Schema para respuesta de préstamo
    id: int
    creado_por: int
    fecha_creacion: date
    activo: bool = True

    model_config = {"from_attributes": True}
