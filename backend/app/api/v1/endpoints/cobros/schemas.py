"""Pydantic schemas for cobros pagos reportados."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.services.cobros.recibo_pdf import WHATSAPP_DISPLAY, WHATSAPP_LINK

class PagoReportadoHistorialItem(BaseModel):
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_email: Optional[str] = None
    motivo: Optional[str] = None
    created_at: Optional[str] = None


class PagoReportadoListItem(BaseModel):
    id: int
    referencia_interna: str
    nombres: str
    apellidos: str
    cedula_display: str
    institucion_financiera: str
    monto: float
    moneda: str
    tasa_cambio_bs_usd: Optional[float] = Field(
        None,
        description="Tasa oficial Bs por 1 USD (día fecha_pago); null si USD o sin tasa en BD.",
    )
    equivalente_usd: Optional[float] = Field(
        None,
        description="Monto en USD (Bs÷tasa si BS; si USD el monto; null si BS sin tasa).",
    )
    fecha_pago: date
    numero_operacion: str
    fecha_reporte: datetime
    estado: str
    gemini_coincide_exacto: Optional[str] = None
    observacion: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    tiene_recibo_pdf: bool
    tiene_comprobante: bool
    canal_ingreso: Optional[str] = Field(
        None,
        description="infopagos | cobros_publico | null (historico). Misma cola operativa y reglas para todos.",
    )
    duplicado_en_pagos: bool = Field(
        False,
        description="True si el comprobante/documento ya existe en tabla `pagos` (cartera).",
    )
    pago_existente_id: Optional[int] = Field(
        None,
        description="ID del registro en `pagos` que tiene el mismo documento.",
    )
    prestamo_existente_id: Optional[int] = Field(
        None,
        description="Préstamo asociado al pago existente en cartera.",
    )
    numero_documento_pago_existente: Optional[str] = Field(
        None,
        description="Valor almacenado en `pagos.numero_documento` del pago existente (referencia para operadores).",
    )
    prestamo_objetivo_id: Optional[int] = None
    prestamo_objetivo_multiple: Optional[bool] = None
    prestamo_duplicado_es_objetivo: Optional[bool] = None


class PagoReportadoDetalle(BaseModel):
    id: int
    referencia_interna: str
    nombres: str
    apellidos: str
    tipo_cedula: str
    numero_cedula: str
    fecha_pago: date
    institucion_financiera: str
    numero_operacion: str
    monto: float
    moneda: str
    tasa_cambio_bs_usd: Optional[float] = Field(
        None,
        description="Tasa oficial Bs por 1 USD (día fecha_pago); null si USD o sin tasa en BD.",
    )
    equivalente_usd: Optional[float] = Field(
        None,
        description="Monto en USD (Bs÷tasa si BS; si USD el monto; null si BS sin tasa).",
    )
    ruta_comprobante: Optional[str] = None
    tiene_comprobante: bool
    tiene_recibo_pdf: bool
    observacion: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    estado: str
    motivo_rechazo: Optional[str] = None
    gemini_coincide_exacto: Optional[str] = None
    gemini_comentario: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    historial: List[PagoReportadoHistorialItem]
    canal_ingreso: Optional[str] = Field(
        None,
        description="infopagos | cobros_publico | null (historico).",
    )
    duplicado_en_pagos: bool = False
    pago_existente_id: Optional[int] = None
    prestamo_existente_id: Optional[int] = None
    pago_existente_estado: Optional[str] = None
    pago_existente_fecha_pago: Optional[date] = Field(
        None,
        description="Fecha del pago ya registrado en cartera (tabla pagos), para comparar con este reporte.",
    )
    prestamo_objetivo_id: Optional[int] = None
    prestamo_objetivo_multiple: Optional[bool] = None
    prestamo_duplicado_es_objetivo: Optional[bool] = None


class PagoReportadoDuplicadoDiagnostico(BaseModel):
    duplicado_en_pagos: bool = False
    pago_existente_id: Optional[int] = None
    prestamo_existente_id: Optional[int] = None
    pago_existente_estado: Optional[str] = None
    pago_existente_fecha_pago: Optional[date] = None
    prestamo_objetivo_id: Optional[int] = None
    prestamo_objetivo_multiple: Optional[bool] = None
    prestamo_duplicado_es_objetivo: Optional[bool] = None


class AprobarRechazarBody(BaseModel):
    motivo: Optional[str] = None


class MarcarExportadosBody(BaseModel):
    pago_reportado_ids: Optional[List[int]] = None

class CambiarEstadoBody(BaseModel):
    estado: str  # pendiente | en_revision | aprobado | rechazado
    motivo: Optional[str] = None


class EditarPagoReportadoBody(BaseModel):
    """Campos editables para que el pago cumpla con los validadores (cédula, fecha, monto, etc.)."""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    tipo_cedula: Optional[str] = None
    numero_cedula: Optional[str] = None
    fecha_pago: Optional[date] = None
    institucion_financiera: Optional[str] = None
    numero_operacion: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    correo_enviado_a: Optional[str] = None
# Mensaje genérico al rechazar: indicar que se comuniquen por WhatsApp (424-4579934)
MENSAJE_RECHAZO_GENERICO = (
    "Su reporte de pago no ha sido aprobado. "
    "Para más información o aclaratorias, comuníquese con nosotros por WhatsApp: {whatsapp} ({link}).\n\n"
    "RapiCredit C.A."
).format(whatsapp=WHATSAPP_DISPLAY, link=WHATSAPP_LINK)
