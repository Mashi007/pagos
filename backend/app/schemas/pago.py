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
    """Schema para respuesta de un pago - FASE 2: Sincronizado con modelo ORM"""

    id: int
    cliente_id: int | None = Field(None, description="ID del cliente")
    fecha_registro: datetime | None = None
    estado: str
    conciliado: bool
    fecha_conciliacion: datetime | None = None
    documento_nombre: str | None = None
    documento_tipo: str | None = None
    documento_ruta: str | None = None
    documento_tamaño: int | None = Field(None, description="Tamaño del documento en bytes")
    documento: str | None = Field(None, description="Documento adicional")
    usuario_registro: str
    activo: bool
    fecha_actualizacion: datetime | None = None
    verificado_concordancia: str | None = None  # SI/NO - Verificación de concordancia con módulo de pagos

    # FASE 2: Campos adicionales sincronizados con ORM
    numero_cuota: int | None = Field(None, description="Número de cuota asociada")
    banco: str | None = Field(None, description="Nombre del banco")
    metodo_pago: str | None = Field(None, description="Método de pago (EFECTIVO, TRANSFERENCIA, etc.)")
    tipo_pago: str | None = Field(None, description="Tipo de pago adicional")
    codigo_pago: str | None = Field(None, description="Código único del pago")
    numero_operacion: str | None = Field(None, description="Número de operación bancaria")
    referencia_pago: str = Field(..., description="Referencia adicional del pago")
    comprobante: str | None = Field(None, description="Ruta o referencia al comprobante")
    monto: int | None = Field(None, description="Monto total (legacy - INTEGER)")
    monto_capital: Decimal | None = Field(None, description="Monto de capital pagado")
    monto_interes: Decimal | None = Field(None, description="Monto de interés pagado")
    monto_cuota_programado: Decimal | None = Field(None, description="Monto de cuota programada")
    monto_mora: Decimal | None = Field(None, description="Monto de mora pagado")
    monto_total: Decimal | None = Field(None, description="Monto total del pago")
    descuento: Decimal | None = Field(None, description="Descuento aplicado")
    dias_mora: int | None = Field(None, description="Días de mora al momento del pago")
    tasa_mora: Decimal | None = Field(None, description="Tasa de mora aplicada (%)")
    fecha_vencimiento: date | None = Field(None, description="Fecha de vencimiento de la cuota")
    hora_pago: str | None = Field(None, description="Hora del pago (TIME)")
    creado_en: datetime | None = Field(None, description="Fecha de creación")
    observaciones: str | None = Field(None, description="Observaciones adicionales del pago")

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
