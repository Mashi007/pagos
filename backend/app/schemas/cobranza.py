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


class CobranzaNotaAdjuntoMeta(BaseModel):
    id: str
    nombre_archivo: Optional[str] = None
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
    adjuntos: List[CobranzaNotaAdjuntoMeta] = Field(default_factory=list)
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


class CobranzaSesionNotaOut(BaseModel):
    """Nueva nota creada al abrir la negociacion (sesion del dia)."""

    nota_id: int
    caso: CobranzaCasoOut


class CobranzaCasoCreate(BaseModel):
    prestamo_id: int
    motivo: str = Field(default="OTRO")
    observaciones: Optional[str] = None


class CobranzaCasoUpdate(BaseModel):
    motivo: Optional[str] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


class CobranzaAcuerdoCreate(BaseModel):
    fecha: Optional[date] = None
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


class UniversoCedulaIn(BaseModel):
    cedula: str


class UniversoCedulasLista(BaseModel):
    cedulas: List[str] = Field(default_factory=list)
    cantidad: int = 0


class UniversoMeta(BaseModel):
    cantidad: int = 0
    cargado_en: Optional[datetime] = None
    usuario_id: Optional[int] = None


class UniversoAnalisisItem(BaseModel):
    prestamo_id: int
    cedula: str
    nombres: Optional[str] = None
    cuotas_vencidas: int = 0
    saldo_vencido_usd: float = 0


class UniversoBucket(BaseModel):
    clave: str
    cantidad: int = 0
    monto_usd: float = 0
    items: List[UniversoAnalisisItem] = Field(default_factory=list)


class UniversoSerieDia(BaseModel):
    fecha: date
    monto_1: float = 0
    monto_2: float = 0
    monto_3: float = 0
    monto_4plus: float = 0


class UniversoAnalisisResponse(BaseModel):
    buckets: dict[str, UniversoBucket]
    sin_vencidas: int = 0
    serie_diaria: List[UniversoSerieDia] = Field(default_factory=list)
    meta: Optional[UniversoMeta] = None
