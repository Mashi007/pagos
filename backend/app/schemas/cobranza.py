"""Schemas API modulo Cobranzas."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


MOTIVOS_COBRANZA = frozenset(
    {"ATRASO_CRONICO", "SOBREPAGO", "NEGOCIACION", "OTRO"}
)
ESTADOS_CASO = frozenset({"ABIERTO", "EN_GESTION", "CERRADO"})
ESTADOS_ACUERDO = frozenset({"PENDIENTE", "CUMPLIDO", "INCUMPLIDO"})
MONEDAS_ACUERDO = frozenset({"USD", "BS"})


class CobranzaPrestamoResumen(BaseModel):
    id: int
    cliente_id: Optional[int] = None
    cedula: str
    nombres: Optional[str] = None
    total_financiamiento: float = 0
    saldo_pendiente: float = 0
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    estado: str
    cuotas_atrasadas: int = 0
    caso_id: Optional[int] = None
    caso_estado: Optional[str] = None
    caso_motivo: Optional[str] = None


class CobranzaBuscarResponse(BaseModel):
    cedula: str
    cliente_id: Optional[int] = None
    nombres: Optional[str] = None
    prestamos: List[CobranzaPrestamoResumen] = Field(default_factory=list)


class CobranzaImagenMeta(BaseModel):
    id: str
    descripcion: Optional[str] = None
    content_type: str
    creado_en: Optional[datetime] = None


class CobranzaAcuerdoOut(BaseModel):
    id: int
    caso_id: int
    fecha: date
    mensaje: str
    cantidad: Optional[float] = None
    moneda: str
    estado: str
    fecha_compromiso: Optional[date] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

    class Config:
        from_attributes = True


class CobranzaCasoOut(BaseModel):
    id: int
    prestamo_id: int
    cliente_id: Optional[int] = None
    cedula: str
    nombres: Optional[str] = None
    motivo: str
    estado: str
    observaciones: Optional[str] = None
    monto_financiamiento: Optional[float] = None
    saldo_pendiente_snapshot: Optional[float] = None
    cuotas_atrasadas_snapshot: Optional[int] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None
    saldo_pendiente_actual: Optional[float] = None
    cuotas_atrasadas_actual: Optional[int] = None
    total_financiamiento_actual: Optional[float] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    prestamo_estado: Optional[str] = None
    imagenes: List[CobranzaImagenMeta] = Field(default_factory=list)
    acuerdos: List[CobranzaAcuerdoOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CobranzaCasoCreate(BaseModel):
    prestamo_id: int
    motivo: str = Field(default="OTRO")
    observaciones: Optional[str] = None


class CobranzaCasoUpdate(BaseModel):
    motivo: Optional[str] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


class CobranzaAcuerdoCreate(BaseModel):
    fecha: date
    mensaje: str = Field(min_length=1)
    cantidad: Optional[float] = Field(default=None, ge=0)
    moneda: str = Field(default="USD")
    fecha_compromiso: Optional[date] = None

    @field_validator("moneda")
    @classmethod
    def moneda_valida(cls, v: str) -> str:
        m = (v or "USD").strip().upper()
        if m not in MONEDAS_ACUERDO:
            raise ValueError("Moneda debe ser USD o BS")
        return m


class CobranzaAcuerdoUpdate(BaseModel):
    fecha: Optional[date] = None
    mensaje: Optional[str] = None
    cantidad: Optional[float] = Field(default=None, ge=0)
    moneda: Optional[str] = None
    fecha_compromiso: Optional[date] = None
    estado: Optional[str] = None

    @field_validator("moneda")
    @classmethod
    def moneda_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        m = v.strip().upper()
        if m not in MONEDAS_ACUERDO:
            raise ValueError("Moneda debe ser USD o BS")
        return m
