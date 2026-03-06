"""
Schemas Pydantic para Préstamo (request/response).
Alineados con la tabla public.prestamos en la BD (columnas confirmadas).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

PRESTAMO_ESTADOS_VALIDOS = frozenset({"APROBADO", "DRAFT", "EN_REVISION", "EVALUADO", "RECHAZADO", "DESEMBOLSADO"})

def _normalizar_estado_prestamo(v):
    if not v or not str(v).strip(): return "DRAFT"
    s = str(v).strip().upper()
    if s == "PROBADO": return "APROBADO"
    if s == "RAFT": return "DRAFT"
    return s


class PrestamoBase(BaseModel):
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: str = ""
    modalidad_pago: Optional[str] = None  # MENSUAL, QUINCENAL, SEMANAL
    numero_cuotas: Optional[int] = None

    @field_validator("numero_cuotas")
    @classmethod
    def numero_cuotas_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 12):
            raise ValueError("numero_cuotas debe estar entre 1 y 12")
        return v

    @field_validator("estado")
    @classmethod
    def estado_normalizado(cls, v: Optional[str]) -> str:
        return _normalizar_estado_prestamo(v or "DRAFT")

    fecha_requerimiento: Optional[date] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoCreate(PrestamoBase):
    """Campos para crear préstamo. cedula/nombres se rellenan desde Cliente si no se envían."""
    aprobado_por_carga_masiva: Optional[bool] = False  # Si True: estado=APROBADO, fecha_aprobacion=fecha_requerimiento


class PrestamoUpdate(BaseModel):
    """Campos opcionales para actualizar."""
    cliente_id: Optional[int] = None
    total_financiamiento: Optional[Decimal] = None
    estado: Optional[str] = None
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None

    @field_validator("numero_cuotas")
    @classmethod
    def numero_cuotas_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 12):
            raise ValueError("numero_cuotas debe estar entre 1 y 12")
        return v

    @field_validator("estado")
    @classmethod
    def estado_normalizado(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return None
        return _normalizar_estado_prestamo(v)

    fecha_requerimiento: Optional[date] = None
    cuota_periodo: Optional[Decimal] = None
    producto: Optional[str] = None


class PrestamoResponse(BaseModel):
    """Respuesta de préstamo (columnas de la tabla prestamos)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    total_financiamiento: Decimal
    estado: str = "DRAFT"
    concesionario: Optional[str] = None
    modelo: Optional[str] = None
    analista: Optional[str] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    fecha_registro: Optional[datetime] = None
    fecha_aprobacion: Optional[datetime] = None
    # Campos para detalle (cedula/nombres en prestamos; cuota_periodo, etc.)
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    cuota_periodo: Optional[Decimal] = None
    fecha_requerimiento: Optional[date] = None
    tasa_interes: Optional[Decimal] = Decimal("0.00")  # Siempre 0% por defecto (producto sin interés)
    producto: Optional[str] = None


class PrestamoListResponse(PrestamoResponse):
    """Préstamo para listado: incluye nombres y cedula del cliente (join)."""
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    numero_cuotas: Optional[int] = None
    modalidad_pago: Optional[str] = None
    revision_manual_estado: Optional[str] = None  # pendiente | revisando | revisado (None si no tiene)
