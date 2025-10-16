# backend/app/schemas/modelo_vehiculo.py
"""
Schemas Pydantic para modelos de vehículos
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class ModeloVehiculoBase(BaseModel):
    modelo: str = Field(..., min_length=1, max_length=100, description="Modelo del vehículo")
    activo: bool = Field(True, description="Si el modelo está activo")

    @field_validator('modelo')
    @classmethod
    def validate_modelo(cls, v):
        if v and not v.strip():
            raise ValueError('Campo modelo no puede estar vacío')
        return v.strip().title() if v else v


class ModeloVehiculoCreate(ModeloVehiculoBase):
    """Schema para crear un modelo de vehículo"""
    pass


class ModeloVehiculoUpdate(BaseModel):
    """Schema para actualizar un modelo de vehículo"""
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    activo: Optional[bool] = None


class ModeloVehiculoResponse(ModeloVehiculoBase):
    """Schema para respuesta de modelo de vehículo"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ModeloVehiculoListResponse(BaseModel):
    """Schema para lista de modelos de vehículos"""
    items: List[ModeloVehiculoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ModeloVehiculoActivosResponse(BaseModel):
    """Schema para modelos activos (para formularios)"""
    id: int
    modelo: str
    activo: bool
    
    class Config:
        from_attributes = True


class ModeloVehiculoStatsResponse(BaseModel):
    """Schema para estadísticas de modelos de vehículos"""
    total_modelos: int
    modelos_activos: int
    modelos_inactivos: int
    por_categoria: dict
    por_marca: dict
