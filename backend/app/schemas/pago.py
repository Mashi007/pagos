"""
Schemas para Pagos
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PagoBase(BaseModel):
    """Schema base para pagos"""

    cedula_cliente: str = Field(..., description="Cédula del cliente")
    prestamo_id: int | None = Field(None, description="ID del préstamo")
    fecha_pago: datetime = Field(..., description="Fecha de pago")
    monto_pagado: Decimal = Field(..., description="Monto pagado")
    numero_documento: str = Field(..., description="Número de documento")
    institucion_bancaria: str | None = Field(None, description="Institución bancaria")
    referencia_pago: str = Field(..., description="Referencia de pago")
    notas: str | None = Field(None, description="Notas adicionales")


class PagoCreate(PagoBase):
    """Schema para crear un pago"""

    pass


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""

    fecha_pago: datetime | None = None
    monto_pagado: Decimal | None = None
    numero_documento: str | None = None
    institucion_bancaria: str | None = None
    referencia_pago: str | None = None
    notas: str | None = None


class PagoResponse(PagoBase):
    """Schema para respuesta de un pago"""

    id: int
    fecha_registro: datetime
    estado: str
    conciliado: bool
    fecha_conciliacion: datetime | None
    documento_nombre: str | None
    documento_tipo: str | None
    documento_ruta: str | None
    usuario_registro: str
    activo: bool
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class PagoWithCuotas(PagoResponse):
    """Schema para pago con información de cuotas asociadas"""

    cuotas: list["CuotaResponse"] = []

    class Config:
        from_attributes = True


class CuotaResponse(BaseModel):
    """Schema para respuesta de cuota"""

    id: int
    prestamo_id: int
    numero_cuota: int
    fecha_vencimiento: datetime
    fecha_pago: datetime | None
    monto_cuota: Decimal
    total_pagado: Decimal
    estado: str

    class Config:
        from_attributes = True


# Actualizar referencias circulares
PagoWithCuotas.model_rebuild()
