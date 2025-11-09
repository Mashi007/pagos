"""
Schemas para Variables de Notificaciones
"""

from typing import Optional

from pydantic import BaseModel, Field


class NotificacionVariableBase(BaseModel):
    nombre_variable: str = Field(..., max_length=100, description="Nombre de la variable (ej: nombre_cliente)")
    tabla: str = Field(..., max_length=50, description="Tabla de la base de datos (clientes, prestamos, cuotas, pagos)")
    campo_bd: str = Field(..., max_length=100, description="Campo de la base de datos")
    descripcion: Optional[str] = Field(None, description="Descripción de la variable")
    activa: bool = Field(default=True, description="Si la variable está activa")


class NotificacionVariableCreate(NotificacionVariableBase):
    pass


class NotificacionVariableUpdate(BaseModel):
    nombre_variable: Optional[str] = Field(None, max_length=100)
    tabla: Optional[str] = Field(None, max_length=50)
    campo_bd: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    activa: Optional[bool] = None


class NotificacionVariableResponse(NotificacionVariableBase):
    id: int
    fecha_creacion: Optional[str] = None
    fecha_actualizacion: Optional[str] = None

    class Config:
        from_attributes = True
