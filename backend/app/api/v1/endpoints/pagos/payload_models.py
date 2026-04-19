"""Modelos Pydantic de cuerpos de petición usados por el router de pagos."""

from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.pago import PagoCreate


class MoverRevisarPagosBody(BaseModel):
    """IDs de pagos exportados a Excel para mover a tabla revisar_pagos."""

    pago_ids: list[int]


class GuardarFilaEditableBody(BaseModel):
    """Datos de una fila editable validada para guardar como Pago."""

    cedula: str
    prestamo_id: Optional[int] = None
    monto_pagado: float
    fecha_pago: str  # formato "DD-MM-YYYY"
    numero_documento: Optional[str] = None
    codigo_documento: Optional[str] = None  # Desambigua mismo Nº comprobante (opcional)
    moneda_registro: Optional[str] = "USD"
    tasa_cambio_manual: Optional[float] = None


class ValidarFilasBatchBody(BaseModel):
    """Batch: cédulas contra préstamos; documentos compuestos (comprobante+código) contra pagos y pagos_con_errores."""

    cedulas: list[str] = []
    documentos: list[str] = []  # Solo los no vacíos


class PagoBatchBody(BaseModel):
    """Array de pagos para crear en una sola petición (Guardar todos). Máximo 500 ítems."""

    pagos: list[PagoCreate]

    @field_validator("pagos")
    @classmethod
    def pagos_limite(cls, v: list) -> list:
        if len(v) > 500:
            raise ValueError("Máximo 500 pagos por lote. Divida en varios envíos.")
        return v


class ConsultarCedulasReportarBsBatchBody(BaseModel):
    cedulas: list[str]


class AgregarCedulaReportarBsBody(BaseModel):
    cedula: str
