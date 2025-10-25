from datetime import date
"""Schemas para KPIs (Key Performance Indicators)"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KPIBase(BaseModel):
    """Schema base para KPIs"""
    nombre: str = Field(..., description="Nombre del KPI")
    descripcion: Optional[str] = Field(None, description="Descripción del KPI")
    categoria: Optional[str] = Field(None, description="Categoría del KPI")
    unidad_medida: Optional[str] = Field
        None, description="Unidad de medida (%, $, unidades, etc)"

    model_config = ConfigDict(from_attributes=True)


class KPICreate(KPIBase):
    """Schema para crear un KPI"""
    valor_objetivo: Optional[Decimal] = Field
    periodicidad: Optional[str] = Field
    activo: bool = Field(True, description="Indica si el KPI está activo")


class KPIUpdate(BaseModel):
    """Schema para actualizar un KPI"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    unidad_medida: Optional[str] = None
    valor_objetivo: Optional[Decimal] = None
    periodicidad: Optional[str] = None
    activo: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class KPIResponse(KPIBase):
    """Schema de respuesta para un KPI"""
    id: int
    valor_objetivo: Optional[Decimal] = None
    periodicidad: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class KPIValorBase(BaseModel):
    """Schema base para valores de KPI"""
    kpi_id: int = Field(..., description="ID del KPI")
    valor: Decimal = Field(..., description="Valor medido del KPI")

    model_config = ConfigDict(from_attributes=True)


class KPIValorCreate(KPIValorBase):
    """Schema para registrar un valor de KPI"""
    notas: Optional[str] = Field
    metadata: Optional[Dict[str, Any]] = Field


class KPIValorUpdate(BaseModel):
    """Schema para actualizar un valor de KPI"""
    valor: Optional[Decimal] = None
    notas: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class KPIValorResponse(KPIValorBase):
    """Schema de respuesta para un valor de KPI"""
    id: int
    notas: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class KPIConValores(KPIResponse):
    valores: List[KPIValorResponse] = Field


class KPIEstadisticas(BaseModel):
    """Schema para estadísticas de un KPI"""
    kpi_id: int
    kpi_nombre: str
    valor_actual: Optional[Decimal] = None
    valor_anterior: Optional[Decimal] = None
    valor_promedio: Optional[Decimal] = None
    valor_minimo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    tendencia: Optional[str] = Field
    cumplimiento_objetivo: Optional[float] = Field

    model_config = ConfigDict(from_attributes=True)


class DashboardKPIs(BaseModel):
    """Schema para dashboard con múltiples KPIs"""
    total_kpis: int
    kpis: List[KPIConValores]
    estadisticas_generales: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "KPIBase",
    "KPICreate",
    "KPIUpdate",
    "KPIResponse",
    "KPIValorBase",
    "KPIValorCreate",
    "KPIValorUpdate",
    "KPIValorResponse",
    "KPIConValores",
    "KPIEstadisticas",
    "DashboardKPIs",

"""
"""