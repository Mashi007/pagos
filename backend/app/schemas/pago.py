"""
Schemas para Pagos
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, Field, field_serializer, field_validator


class PagoBase(BaseModel):
    """Schema base para pagos"""

    cedula: str = Field(..., description="Cédula del cliente")  # Unificado con clientes y prestamos
    prestamo_id: int | None = Field(None, description="ID del préstamo")
    fecha_pago: Union[date, datetime, str] = Field(..., description="Fecha de pago")
    monto_pagado: Decimal = Field(..., description="Monto pagado")
    numero_documento: str = Field(..., description="Número de documento")
    institucion_bancaria: str | None = Field(None, description="Institución bancaria")
    notas: str | None = Field(None, description="Notas adicionales")

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def parse_fecha_pago(cls, v):
        """Convertir fecha_pago a datetime si viene como string o date"""
        if isinstance(v, str):
            return cls._parsear_fecha_string(v)
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v

    @staticmethod
    def _parsear_fecha_string(v: str) -> datetime:
        """Intenta parsear una fecha en formato string a datetime"""
        v = v.strip()

        # Intentar formato YYYY-MM-DD
        if len(v) == 10 and v.count("-") == 2:
            try:
                return datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                pass

        # Intentar formato ISO (con Z o sin)
        try:
            v_iso = v.replace("Z", "+00:00")
            return datetime.fromisoformat(v_iso)
        except ValueError:
            pass

        # Intentar otros formatos comunes
        formatos = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
        for formato in formatos:
            try:
                return datetime.strptime(v, formato)
            except ValueError:
                continue

        raise ValueError(f"Formato de fecha inválido: {v}")


class PagoCreate(PagoBase):
    """Schema para crear un pago"""

    pass


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""

    fecha_pago: Union[date, datetime, str] | None = None

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def parse_fecha_pago_update(cls, v):
        """Convertir fecha_pago a datetime si viene como string o date"""
        if v is None:
            return None
        if isinstance(v, str):
            return PagoBase._parsear_fecha_string(v)
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v

    monto_pagado: Decimal | None = None
    numero_documento: str | None = None
    institucion_bancaria: str | None = None
    notas: str | None = None


class PagoResponse(PagoBase):
    """Schema para respuesta de un pago"""

    id: int
    fecha_registro: datetime | None = None
    estado: str
    conciliado: bool
    fecha_conciliacion: datetime | None = None
    documento_nombre: str | None = None
    documento_tipo: str | None = None
    documento_ruta: str | None = None
    usuario_registro: str
    activo: bool
    fecha_actualizacion: datetime | None = None
    verificado_concordancia: str | None = None  # SI/NO - Verificación de concordancia con módulo de pagos

    @field_serializer("monto_pagado")
    @classmethod
    def serialize_monto(cls, v):
        """Serializar Decimal como float"""
        if isinstance(v, Decimal):
            return float(v)
        return v

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
