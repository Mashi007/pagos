"""
Schemas para Pagos
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, Field, field_validator


class PagoBase(BaseModel):
    """Schema base para pagos"""

    cedula_cliente: str = Field(..., description="Cédula del cliente")
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
            # Limpiar string y remover espacios
            v = v.strip()
            # Intentar parsear como fecha (YYYY-MM-DD) primero, que es lo más común
            try:
                # Intentar como fecha simple YYYY-MM-DD y convertir a datetime al inicio del día
                if len(v) == 10 and v.count("-") == 2:
                    return datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                pass
            # Si no es formato simple, intentar como datetime ISO
            try:
                # Reemplazar Z por +00:00 para compatibilidad
                v_iso = v.replace("Z", "+00:00")
                return datetime.fromisoformat(v_iso)
            except ValueError:
                # Si falla, intentar otros formatos comunes
                try:
                    # Formato con espacio en lugar de T
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d %H:%M")
                    except ValueError:
                        raise ValueError(f"Formato de fecha inválido: {v}")
        elif isinstance(v, date) and not isinstance(v, datetime):
            # Si es date pero no datetime, convertir a datetime al inicio del día
            return datetime.combine(v, datetime.min.time())
        return v


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
            # Limpiar string y remover espacios
            v = v.strip()
            # Intentar parsear como fecha (YYYY-MM-DD) primero
            try:
                if len(v) == 10 and v.count("-") == 2:
                    return datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                pass
            # Si no es formato simple, intentar como datetime ISO
            try:
                v_iso = v.replace("Z", "+00:00")
                return datetime.fromisoformat(v_iso)
            except ValueError:
                try:
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d %H:%M")
                    except ValueError:
                        raise ValueError(f"Formato de fecha inválido: {v}")
        elif isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v

    monto_pagado: Decimal | None = None
    numero_documento: str | None = None
    institucion_bancaria: str | None = None
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
