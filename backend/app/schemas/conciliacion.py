from datetime import date
# backend/app/schemas/conciliacion.py
"""Schemas para el módulo de conciliación bancaria"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constantes de validación
MAX_CONFIDENCE = 100
MIN_YEAR = 2020
MAX_YEAR = 2100
DECIMAL_ZERO = Decimal("0.00")


class EstadoConciliacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONCILIADO = "CONCILIADO"
    CONCILIADO_MANUAL = "CONCILIADO_MANUAL"
    RECHAZADO = "RECHAZADO"
    EN_REVISION = "EN_REVISION"


class TipoMatch(str, Enum):
    REFERENCIA = "referencia"
    MONTO_FECHA = "monto_fecha"
    MANUAL = "manual"


# ============================================
# MOVIMIENTO BANCARIO
# ============================================


class MovimientoBancario(BaseModel):
    """Representa un movimiento del extracto bancario"""
    fecha: date
    referencia: str
    monto: Decimal
    cedula_pagador: Optional[str] = Field
    descripcion: Optional[str] = ""
    cuenta_origen: Optional[str] = Field

    model_config = ConfigDict
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),

    @field_validator("monto")
    @classmethod
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class MovimientoBancarioResponse(MovimientoBancario):
    """Response con información adicional del movimiento"""
    id: Optional[int] = None
    conciliado: bool = False
    pago_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# CONCILIACIÓN
# ============================================


class ConciliacionCreate(BaseModel):
    """Schema para crear una conciliación"""
    fecha_inicio: date
    fecha_fin: date

    @field_validator("fecha_fin")
    @classmethod
    def validar_fechas(cls, v, info):
        if "fecha_inicio" in info.data and v < info.data["fecha_inicio"]:
            raise ValueError
        return v


class ConciliacionMatch(BaseModel):
    """Detalle de un match de conciliación"""
    movimiento_bancario: MovimientoBancario
    pago_id: int
    monto_pago: Decimal
    fecha_pago: date
    tipo_match: TipoMatch
    confianza: float = Field

    model_config = ConfigDict
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),


class ResultadoConciliacion(BaseModel):
    """Resultado del proceso de conciliación"""
    sin_conciliar_banco: int
    sin_conciliar_sistema: int
    porcentaje_conciliacion: float = 0.0
    detalle_sin_conciliar_banco: List[MovimientoBancario] = []
    detalle_sin_conciliar_sistema: List[Dict[str, Any]] = []

    @field_validator("porcentaje_conciliacion")
    @classmethod
    def calcular_porcentaje(cls, v, info):
        if 
            return round
                * 100,
                2,
        return 0.0


    class Config:


class ConciliacionResponse(BaseModel):
    """Response de conciliación guardada"""
    id: int
    fecha_inicio: date
    fecha_fin: date
    estado: EstadoConciliacion

    model_config = ConfigDict
            date: lambda v: v.isoformat(),
        },


# ============================================
# CONFIRMACIÓN MANUAL
# ============================================


class ConfirmacionConciliacion(BaseModel):
    """Schema para confirmar manualmente una conciliación"""
    pago_id: int
    movimiento_id: Optional[int] = None
    referencia_bancaria: str
    observaciones: Optional[str] = None

    @field_validator("referencia_bancaria")
    @classmethod
    def validar_referencia(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("La referencia bancaria es obligatoria")
        return v.strip()


class ConfirmacionResponse(BaseModel):
    """Response de confirmación de conciliación"""
    success: bool
    message: str
    pago_id: int
    referencia_bancaria: str


    class Config:


# ============================================
# REPORTES
# ============================================


class ReporteConciliacionMensual(BaseModel):
    """Reporte mensual de conciliación"""
    mes: int = Field(ge=1, le=12)
    anio: int = Field(ge=MIN_YEAR, le=MAX_YEAR)
    pendientes: int
    porcentaje_conciliacion: float
    monto_total: Decimal = DECIMAL_ZERO
    monto_conciliado: Decimal = DECIMAL_ZERO


    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


class FiltroConciliacion(BaseModel):
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    estado: Optional[EstadoConciliacion] = None
    monto_min: Optional[Decimal] = None
    monto_max: Optional[Decimal] = None
    referencia: Optional[str] = None


    class Config:
        json_encoders = 


# ============================================
# PENDIENTES
# ============================================


class PagoPendienteConciliacion(BaseModel):
    """Pago pendiente de conciliar"""
    id: int
    prestamo_id: int
    cuota_id: Optional[int] = None
    monto: Decimal
    fecha_pago: date
    concepto: str
    dias_pendiente: int = 0

    model_config = ConfigDict
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
        },


# ============================================
# CARGA DE EXTRACTO
# ============================================


class ExtractoBancarioUpload(BaseModel):
    """Configuración para carga de extracto"""
    banco: str
    formato: str = "CSV"
    separador: str = ","
    codificacion: str = "utf-8"
    tiene_encabezado: bool = True
    columnas: Dict[str, str] = 


class ValidacionExtracto(BaseModel):
    """Resultado de validación de extracto"""
    valido: bool
    errores: List[str] = []
    advertencias: List[str] = []


# ============================================
# ESTADÍSTICAS
# ============================================


class EstadisticasConciliacion(BaseModel):
    """Estadísticas generales de conciliación"""
    total_procesado: int
    tasa_conciliacion: float  # Porcentaje
    tiempo_promedio_conciliacion: float  # En días
    total_diferencias: Decimal
    por_estado: Dict[str, int] = {}
    por_mes: Dict[str, int] = {}


    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


# ============================================
# SCHEMAS PARA FUNCIONALIDAD AVANZADA
# ============================================


class MovimientoBancarioExtendido(MovimientoBancario):
    """Movimiento bancario con información de matching"""
    id: Optional[int] = None
    tipo_match: Optional[TipoMatch] = None
    confianza_match: Optional[float] = None
    cliente_encontrado: Optional[dict] = None
    pago_sugerido: Optional[dict] = None
    requiere_revision: bool = False

    model_config = ConfigDict(from_attributes=True)


class ValidacionArchivoBancario(BaseModel):
    """Resultado de validación de archivo bancario"""
    archivo_valido: bool
    formato_detectado: str  # CSV, EXCEL
    total_filas: int
    filas_validas: int
    errores: List[str] = []
    advertencias: List[str] = []
    cedulas_no_registradas: List[str] = []
    vista_previa: List[MovimientoBancarioExtendido] = []


class ConciliacionMasiva(BaseModel):
    """Schema para conciliación masiva"""
        True, description="Aplicar coincidencias exactas automáticamente"
    aplicar_parciales: bool = Field
    observaciones: Optional[str] = None


class ResultadoConciliacionMasiva(BaseModel):
    """Resultado de conciliación masiva"""
    errores: List[dict] = []
    resumen_financiero: dict
    reporte_generado: bool = True


    class Config:


class RevisionManual(BaseModel):
    """Schema para revisión manual de movimiento"""
    movimiento_id: int
    cliente_cedula: str
    cuota_id: Optional[int] = None
    monto_ajustado: Optional[Decimal] = None
    observaciones: str
    accion: str = Field(..., pattern="^(APLICAR|RECHAZAR|NO_APLICABLE)$")


class HistorialConciliacion(BaseModel):
    """Historial de conciliaciones"""
    id: int
    usuario_proceso: str
    archivo_original: str
    tasa_exito: float
    estado: EstadoConciliacion
    observaciones: Optional[str] = None

    model_config = ConfigDict
