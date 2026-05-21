"""Schemas API modulo Cobranzas."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


MOTIVOS_COBRANZA = frozenset(
    {"ATRASO_CRONICO", "SOBREPAGO", "NEGOCIACION", "OTRO"}
)
ESTADOS_CASO = frozenset({"ABIERTO", "EN_GESTION", "CERRADO"})
ESTADOS_ACUERDO = frozenset({"PENDIENTE", "CUMPLIDO", "INCUMPLIDO"})


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
    fecha_acuerdo: date
    fecha_compromiso: Optional[date] = None
    notas: str
    estado: str
    monto_compromiso: Optional[float] = None
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
    fecha_acuerdo: date
    fecha_compromiso: Optional[date] = None
    notas: str = Field(min_length=1)
    monto_compromiso: Optional[float] = None


class CobranzaAcuerdoUpdate(BaseModel):
    fecha_acuerdo: Optional[date] = None
    fecha_compromiso: Optional[date] = None
    notas: Optional[str] = None
    monto_compromiso: Optional[float] = None
    estado: Optional[str] = None
