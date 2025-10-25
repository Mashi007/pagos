from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class AprobacionBase(BaseModel):
    # Schema base para Aprobación
    tipo: str = Field(..., description="Tipo de aprobación")
    descripcion: str = Field(..., description="Descripción de la solicitud")
    monto: Optional[float] = Field(None, description="Monto relacionado")
    datos_adicionales: Optional[dict] = Field(None, description="Datos adicionales")


class AprobacionCreate(AprobacionBase):
    # Schema para crear aprobación
    pass


class AprobacionUpdate(BaseModel):
    # Schema para actualizar aprobación
    descripcion: Optional[str] = None
    monto: Optional[float] = None
    datos_adicionales: Optional[dict] = None


class AprobacionResponse(AprobacionBase):
    # Schema para respuesta de aprobación
    id: int
    estado: str
    solicitado_por: int
    aprobado_por: Optional[int] = None
    fecha_solicitud: date
    fecha_aprobacion: Optional[date] = None
    observaciones_aprobacion: Optional[str] = None

    model_config = {"from_attributes": True}
