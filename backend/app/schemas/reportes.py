# backend/app/schemas/reportes.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal


class FiltrosReporte(BaseModel):
    """Filtros comunes para reportes"""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    cliente_id: Optional[int] = None
    estado: Optional[str] = None
    tipo_prestamo: Optional[str] = None


class DistribucionMonto(BaseModel):
    """Distribución por rango de montos"""
    rango: str
    cantidad: int
    monto: Decimal

    class Config:
        from_attributes = True


class ReporteCartera(BaseModel):
    """Esquema para reporte de cartera"""
    fecha_corte: date
    cartera_total: Decimal
    capital_pendiente: Decimal
    intereses_pendientes: Decimal
    total_prestamos_activos: int
    total_prestamos_mora: int
    tasa_morosidad: float
    distribucion_montos: List[Dict[str, Any]]

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class RangoMorosidad(BaseModel):
    """Detalle por rango de morosidad"""
    rango: str
    cantidad: int
    monto_total: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class ReporteMorosidad(BaseModel):
    """Esquema para reporte de morosidad"""
    fecha_reporte: date
    total_prestamos_mora: int
    monto_total_mora: Decimal
    detalle_por_rango: List[Dict[str, Any]]

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class DetalleConcepto(BaseModel):
    """Detalle de pagos por concepto"""
    concepto: str
    cantidad: int
    monto: Decimal

    class Config:
        from_attributes = True


class ReporteCobranza(BaseModel):
    """Esquema para reporte de cobranza"""
    fecha_inicio: date
    fecha_fin: date
    total_recaudado: Decimal
    cantidad_pagos: int
    promedio_pago: Decimal
    detalle_por_concepto: List[Dict[str, Any]]
    eficiencia_cobranza: float

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class ReporteVencimientos(BaseModel):
    """Reporte de cuotas por vencer"""
    fecha_inicio: date
    fecha_fin: date
    total_cuotas: int
    monto_total: Decimal
    detalle: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class ReporteRendimiento(BaseModel):
    """Reporte de rendimiento del portafolio"""
    periodo: str
    total_desembolsado: Decimal
    total_recuperado: Decimal
    tasa_recuperacion: float
    roi: float
    prestamos_otorgados: int
    prestamos_liquidados: int

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class ClienteTop(BaseModel):
    """Cliente top por volumen"""
    cliente_id: int
    nombre: str
    total_prestamos: int
    monto_total: Decimal
    promedio_pago: float
    calificacion: Optional[str] = None

    class Config:
        from_attributes = True


class ReporteClientesTop(BaseModel):
    """Reporte de mejores clientes"""
    fecha_reporte: date
    criterio: str  # 'monto', 'cantidad', 'puntualidad'
    top_clientes: List[ClienteTop]

    class Config:
        from_attributes = True
