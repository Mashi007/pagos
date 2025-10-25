# backend/app/schemas/reportes.py

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    cliente_id: Optional[int] = None
    estado: Optional[str] = None
    tipo_prestamo: Optional[str] = None


class DistribucionMonto(BaseModel):
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


    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}


    rango: str
    cantidad: int
    monto_total: Decimal

    model_config = ConfigDict(from_attributes=True)


    fecha_reporte: date
    monto_total_mora: Decimal
    detalle_por_rango: List[Dict[str, Any]]


    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}


class DetalleConcepto(BaseModel):
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
    promedio_pago: Decimal
    detalle_por_concepto: List[Dict[str, Any]]
    eficiencia_cobranza: float


    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}


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


    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}


class ClienteTop(BaseModel):
    """Cliente top por volumen"""
    cliente_id: int
    nombre: str
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
