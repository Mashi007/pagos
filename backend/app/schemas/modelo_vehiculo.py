# backend/app/schemas/modelo_vehiculo.py
"""
Schemas para ModeloVehiculo
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModeloVehiculoBase(BaseModel):
    """Schema base para ModeloVehiculo"""

    modelo: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del modelo de vehículo"
    )
    activo: bool = Field(default=True, description="Estado del modelo")


class ModeloVehiculoCreate(ModeloVehiculoBase):
    """Schema para crear un modelo de vehículo"""


class ModeloVehiculoUpdate(BaseModel):
    """Schema para actualizar un modelo de vehículo"""

    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    activo: Optional[bool] = None


class ModeloVehiculoResponse(ModeloVehiculoBase):
    """Schema de respuesta para ModeloVehiculo"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ModeloVehiculoListResponse(BaseModel):
    """Schema para respuesta de lista paginada"""

    items: list[ModeloVehiculoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
