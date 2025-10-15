# backend/app/schemas/modelo_vehiculo.py
"""
Schemas Pydantic para modelos de vehículos
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class ModeloVehiculoBase(BaseModel):
    marca: str = Field(..., min_length=2, max_length=50, description="Marca del vehículo")
    modelo: str = Field(..., min_length=1, max_length=100, description="Modelo del vehículo")
    categoria: Optional[str] = Field(None, max_length=50, description="Categoría del vehículo")
    precio_base: Optional[Decimal] = Field(None, ge=0, description="Precio base del vehículo")
    activo: bool = Field(True, description="Si el modelo está activo")
    descripcion: Optional[str] = Field(None, description="Descripción del modelo")
    especificaciones: Optional[str] = Field(None, description="Especificaciones técnicas")

    @validator('marca', 'modelo')
    def validate_text_fields(cls, v):
        if v and not v.strip():
            raise ValueError('Campo no puede estar vacío')
        return v.strip().title() if v else v

    @validator('categoria')
    def validate_categoria(cls, v):
        if v:
            categorias_validas = ['Sedán', 'SUV', 'Hatchback', 'Pickup', 'Motocicleta', 'Camioneta', 'Van']
            if v not in categorias_validas:
                raise ValueError(f'Categoría debe ser una de: {", ".join(categorias_validas)}')
        return v


class ModeloVehiculoCreate(ModeloVehiculoBase):
    """Schema para crear un modelo de vehículo"""
    pass


class ModeloVehiculoUpdate(BaseModel):
    """Schema para actualizar un modelo de vehículo"""
    marca: Optional[str] = Field(None, min_length=2, max_length=50)
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    categoria: Optional[str] = Field(None, max_length=50)
    precio_base: Optional[Decimal] = Field(None, ge=0)
    activo: Optional[bool] = None
    descripcion: Optional[str] = None
    especificaciones: Optional[str] = None


class ModeloVehiculoResponse(ModeloVehiculoBase):
    """Schema para respuesta de modelo de vehículo"""
    id: int
    nombre_completo: str = Field(..., description="Nombre completo del modelo")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    nombre_completo: str
    marca: str
    modelo: str
    categoria: Optional[str]
    precio_base: Optional[Decimal]
    
    class Config:
        from_attributes = True


class ModeloVehiculoStatsResponse(BaseModel):
    """Schema para estadísticas de modelos de vehículos"""
    total_modelos: int
    modelos_activos: int
    modelos_inactivos: int
    por_categoria: dict
    por_marca: dict
