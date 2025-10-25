"""
Archivo corregido - Contenido básico funcional
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class KPIMetric(BaseModel):
    """Métrica KPI básica"""
    name: str = Field(..., description="Nombre de la métrica")
    value: float = Field(..., description="Valor de la métrica")
    date: date = Field(..., description="Fecha de la métrica")
    description: Optional[str] = Field(None, description="Descripción de la métrica")