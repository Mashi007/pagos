"""
Schemas para Plantillas de Notificaciones
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificacionPlantillaBase(BaseModel):
    """Schema base para plantillas de notificaciones"""

    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    tipo: str = Field(..., description="Tipo de notificación")
    asunto: str = Field(..., min_length=1, max_length=200)
    cuerpo: str = Field(..., min_length=1)
    variables_disponibles: Optional[str] = Field(None, description="Variables disponibles en JSON")
    activa: bool = True
    zona_horaria: str = Field(default="America/Caracas", max_length=50)


class NotificacionPlantillaCreate(NotificacionPlantillaBase):
    """Schema para crear una plantilla"""

    pass


class NotificacionPlantillaUpdate(BaseModel):
    """Schema para actualizar una plantilla"""

    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    asunto: Optional[str] = Field(None, min_length=1, max_length=200)
    cuerpo: Optional[str] = Field(None, min_length=1)
    variables_disponibles: Optional[str] = None
    activa: Optional[bool] = None
    zona_horaria: Optional[str] = Field(None, max_length=50)


class NotificacionPlantillaResponse(NotificacionPlantillaBase):
    """Schema para respuesta de plantilla"""

    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class EnviarNotificacionRequest(BaseModel):
    """Schema para enviar notificación con plantilla"""

    template_id: int
    cliente_id: int
    variables: dict = Field(default_factory=dict, description="Valores para las variables de la plantilla")
