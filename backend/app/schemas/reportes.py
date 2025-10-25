"""
Archivo corregido - Contenido básico funcional
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ReporteBase(BaseModel):
    """Base para reportes"""

    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    tipo_reporte: str = Field(..., description="Tipo de reporte")


class ReporteResponse(ReporteBase):
    """Respuesta de reporte"""

    id: int
    contenido: str
    fecha_generacion: date
