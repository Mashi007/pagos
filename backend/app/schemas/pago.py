"""
Schemas Pydantic para Pago (registro de pagos). Alineados con el frontend.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Límite de INTEGER en PostgreSQL (evita 500 cuando se envía número de documento como prestamo_id)
PRESTAMO_ID_MAX = 2147483647


class PagoCreate(BaseModel):
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: date
    monto_pagado: Decimal
    numero_documento: str  # Cualquier formato. ÚNICA regla: no duplicado en el sistema.
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None  # Sí/No en carga masiva

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato(cls, v: object) -> str:
        """Acepta cualquier formato; no se valida contenido. Solo se normaliza a string."""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("prestamo_id")
    @classmethod
    def prestamo_id_en_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 1 or v > PRESTAMO_ID_MAX:
            raise ValueError(
                f"prestamo_id debe estar entre 1 y {PRESTAMO_ID_MAX}. "
                "Si el valor parece un número de documento (ej. 740087408451411), elija el crédito correcto en la lista."
            )
        return v


class PagoUpdate(BaseModel):
    cedula_cliente: Optional[str] = None
    prestamo_id: Optional[int] = None
    fecha_pago: Optional[date] = None
    monto_pagado: Optional[Decimal] = None
    numero_documento: Optional[str] = None  # Cualquier formato. ÚNICA regla: no duplicado en el sistema.
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None
    verificado_concordancia: Optional[str] = None  # SI / NO

    @field_validator("numero_documento", mode="before")
    @classmethod
    def numero_documento_cualquier_formato(cls, v: object) -> Optional[str]:
        """Acepta cualquier formato; no se valida contenido. Solo se normaliza a string o None."""
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("prestamo_id")
    @classmethod
    def prestamo_id_en_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 1 or v > PRESTAMO_ID_MAX:
            raise ValueError(
                f"prestamo_id debe estar entre 1 y {PRESTAMO_ID_MAX}. "
                "Si el valor parece un número de documento, elija el crédito correcto."
            )
        return v


class PagoResponse(BaseModel):
    """Respuesta de un pago (para GET por id y para items de lista)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: date
    monto_pagado: Decimal
    numero_documento: str
    institucion_bancaria: Optional[str] = None
    estado: str
    fecha_registro: Optional[datetime] = None
    fecha_conciliacion: Optional[datetime] = None
    conciliado: bool = False
    verificado_concordancia: Optional[str] = None
    usuario_registro: Optional[str] = None
    notas: Optional[str] = None
    documento_nombre: Optional[str] = None
    documento_tipo: Optional[str] = None
    documento_ruta: Optional[str] = None
    cuotas_atrasadas: Optional[int] = None  # calculado en listado
