"""
Schemas Pydantic para Pago (registro de pagos). Alineados con el frontend.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PagoCreate(BaseModel):
    cedula_cliente: str
    prestamo_id: Optional[int] = None
    fecha_pago: date
    monto_pagado: Decimal
    numero_documento: str
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None


class PagoUpdate(BaseModel):
    cedula_cliente: Optional[str] = None
    prestamo_id: Optional[int] = None
    fecha_pago: Optional[date] = None
    monto_pagado: Optional[Decimal] = None
    numero_documento: Optional[str] = None
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None


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
