# backend/app/schemas/conciliacion.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class EstadoConciliacion(str, Enum):
    """Estados posibles de conciliación"""
    PENDIENTE = "PENDIENTE"
    CONCILIADO = "CONCILIADO"
    CONCILIADO_MANUAL = "CONCILIADO_MANUAL"
    RECHAZADO = "RECHAZADO"
    EN_REVISION = "EN_REVISION"


class TipoMatch(str, Enum):
    """Tipos de match en conciliación"""
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
    descripcion: Optional[str] = ""
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }
    
    @validator('monto')
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError('El monto debe ser mayor a 0')
        return v


class MovimientoBancarioResponse(MovimientoBancario):
    """Response con información adicional del movimiento"""
    id: Optional[int] = None
    conciliado: bool = False
    pago_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# ============================================
# CONCILIACIÓN
# ============================================

class ConciliacionCreate(BaseModel):
    """Schema para crear una conciliación"""
    fecha_inicio: date
    fecha_fin: date
    movimientos: List[MovimientoBancario]
    
    @validator('fecha_fin')
    def validar_fechas(cls, v, values):
        if 'fecha_inicio' in values and v < values['fecha_inicio']:
            raise ValueError('La fecha fin debe ser posterior a la fecha inicio')
        return v


class ConciliacionMatch(BaseModel):
    """Detalle de un match de conciliación"""
    movimiento_bancario: MovimientoBancario
    pago_id: int
    monto_pago: Decimal
    fecha_pago: date
    tipo_match: TipoMatch
    confianza: float = Field(ge=0, le=100, description="Porcentaje de confianza del match")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class ResultadoConciliacion(BaseModel):
    """Resultado del proceso de conciliación"""
    total_movimientos: int
    total_pagos: int
    conciliados: int
    sin_conciliar_banco: int
    sin_conciliar_sistema: int
    porcentaje_conciliacion: float = 0.0
    
    detalle_conciliados: List[Dict[str, Any]] = []
    detalle_sin_conciliar_banco: List[MovimientoBancario] = []
    detalle_sin_conciliar_sistema: List[Dict[str, Any]] = []
    
    fecha_proceso: datetime = Field(default_factory=datetime.now)
    
    @validator('porcentaje_conciliacion', always=True)
    def calcular_porcentaje(cls, v, values):
        if 'total_movimientos' in values and values['total_movimientos'] > 0:
            return round((values.get('conciliados', 0) / values['total_movimientos']) * 100, 2)
        return 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConciliacionResponse(BaseModel):
    """Response de conciliación guardada"""
    id: int
    fecha_inicio: date
    fecha_fin: date
    total_movimientos: int
    total_conciliados: int
    estado: EstadoConciliacion
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }


# ============================================
# CONFIRMACIÓN MANUAL
# ============================================

class ConfirmacionConciliacion(BaseModel):
    """Schema para confirmar manualmente una conciliación"""
    pago_id: int
    movimiento_id: Optional[int] = None
    referencia_bancaria: str
    observaciones: Optional[str] = None
    
    @validator('referencia_bancaria')
    def validar_referencia(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('La referencia bancaria es obligatoria')
        return v.strip()


class ConfirmacionResponse(BaseModel):
    """Response de confirmación de conciliación"""
    success: bool
    message: str
    pago_id: int
    referencia_bancaria: str
    fecha_conciliacion: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# REPORTES
# ============================================

class ReporteConciliacionMensual(BaseModel):
    """Reporte mensual de conciliación"""
    mes: int = Field(ge=1, le=12)
    anio: int = Field(ge=2020, le=2100)
    total_pagos: int
    conciliados: int
    pendientes: int
    porcentaje_conciliacion: float
    monto_total: Decimal = Decimal("0.00")
    monto_conciliado: Decimal = Decimal("0.00")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class FiltroConciliacion(BaseModel):
    """Filtros para búsqueda de conciliaciones"""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    estado: Optional[EstadoConciliacion] = None
    monto_min: Optional[Decimal] = None
    monto_max: Optional[Decimal] = None
    referencia: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None
        }


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
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


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
    
    columnas: Dict[str, str] = {
        "fecha": "fecha",
        "referencia": "referencia", 
        "monto": "monto",
        "descripcion": "descripcion"
    }


class ValidacionExtracto(BaseModel):
    """Resultado de validación de extracto"""
    valido: bool
    errores: List[str] = []
    advertencias: List[str] = []
    total_movimientos: int = 0
    movimientos_validos: int = 0
    
    
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
        json_encoders = {
            Decimal: lambda v: float(v)
        }
