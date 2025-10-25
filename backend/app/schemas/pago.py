from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constantes de validación
MIN_CEDULA_LENGTH = 8
MAX_CEDULA_LENGTH = 20
MIN_DOCUMENTO_LENGTH = 1
MAX_DOCUMENTO_LENGTH = 100
MAX_DOCUMENTO_NOMBRE_LENGTH = 255
MAX_DOCUMENTO_TIPO_LENGTH = 10
MAX_DOCUMENTO_RUTA_LENGTH = 500
MAX_NOTA_LENGTH = 1000


class PagoBase(BaseModel):
    """Schema base para pagos"""

    cedula_cliente: str = Field(
        ...,
        min_length=MIN_CEDULA_LENGTH,
        max_length=MAX_CEDULA_LENGTH,
        description="Cédula del cliente",
    )
    fecha_pago: datetime = Field(..., description="Fecha del pago")
    monto_pagado: float = Field(..., gt=0, description="Monto pagado")
    numero_documento: str = Field(
        ...,
        min_length=MIN_DOCUMENTO_LENGTH,
        max_length=MAX_DOCUMENTO_LENGTH,
        description="Número de documento",
    )
    documento_nombre: Optional[str] = Field(
        None,
        max_length=MAX_DOCUMENTO_NOMBRE_LENGTH,
        description="Nombre del documento",
    )
    documento_tipo: Optional[str] = Field(
        None,
        max_length=MAX_DOCUMENTO_TIPO_LENGTH,
        description="Tipo de documento",
    )
    documento_tamaño: Optional[int] = Field(
        None, ge=0, description="Tamaño del documento en bytes"
    )
    documento_ruta: Optional[str] = Field(
        None,
        max_length=MAX_DOCUMENTO_RUTA_LENGTH,
        description="Ruta del documento",
    )
    notas: Optional[str] = Field(None, description="Notas adicionales")

    @field_validator("cedula_cliente")
    @classmethod
    def validate_cedula(cls, v):
        if not v or len(v.strip()) < MIN_CEDULA_LENGTH:
            raise ValueError(
                f"Cédula debe tener al menos {MIN_CEDULA_LENGTH} caracteres"
            )
        return v.strip().upper()

    @field_validator("numero_documento")
    @classmethod
    def validate_numero_documento(cls, v):
        if not v or len(v.strip()) < MIN_DOCUMENTO_LENGTH:
            raise ValueError("Número de documento es requerido")
        return v.strip()

    @field_validator("documento_tipo")
    @classmethod
    def validate_documento_tipo(cls, v):
        if v and v.upper() not in ["PNG", "JPG", "PDF"]:
            raise ValueError("Tipo de documento debe ser PNG, JPG o PDF")
        return v.upper() if v else v


class PagoCreate(PagoBase):
    """Schema para crear un pago"""


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""

    fecha_pago: Optional[datetime] = None
    monto_pagado: Optional[float] = Field(None, gt=0)
    numero_documento: Optional[str] = Field(None, min_length=1, max_length=100)
    documento_nombre: Optional[str] = Field(None, max_length=255)
    documento_tipo: Optional[str] = Field(None, max_length=10)
    documento_tamaño: Optional[int] = Field(None, ge=0)
    documento_ruta: Optional[str] = Field(None, max_length=500)
    notas: Optional[str] = None
    activo: Optional[bool] = None


class PagoResponse(PagoBase):
    """Schema para respuesta de pago"""

    id: int
    conciliado: bool
    fecha_conciliacion: Optional[datetime]
    activo: bool
    fecha_registro: datetime
    fecha_actualizacion: datetime

    model_config = ConfigDict(from_attributes=True)


class PagoListResponse(BaseModel):
    """Schema para lista de pagos"""

    pagos: List[PagoResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


class ConciliacionBase(BaseModel):
    """Schema base para conciliación"""

    cedula_cliente: str = Field(..., min_length=8, max_length=20)
    numero_documento_anterior: str = Field(..., min_length=1, max_length=100)
    numero_documento_nuevo: str = Field(..., min_length=1, max_length=100)
    cedula_nueva: str = Field(..., min_length=8, max_length=20)
    nota: str = Field(..., min_length=1, description="Nota explicativa")


class ConciliacionCreate(ConciliacionBase):
    """Schema para crear conciliación"""


class ConciliacionResponse(ConciliacionBase):
    """Schema para respuesta de conciliación"""

    id: int
    fecha: datetime
    responsable: str
    pago_id: int

    model_config = ConfigDict(from_attributes=True)


class KPIsPagos(BaseModel):
    """Schema para KPIs de pagos"""

    total_pagos: int
    total_dolares: float
    numero_pagos: int
    cantidad_conciliada: int
    cantidad_no_conciliada: int
    fecha_actualizacion: datetime


class ResumenCliente(BaseModel):
    """Schema para resumen de pagos por cliente"""

    cedula_cliente: str
    total_pagado: float
    total_conciliado: float
    total_pendiente: float
    numero_pagos: int
    ultimo_pago: Optional[datetime]
    estado_conciliacion: str  # CONCILIADO, PENDIENTE, PARCIAL