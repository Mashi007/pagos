"""
Schemas Pydantic para Ticket (CRM).
Alineados con el frontend (Ticket, TicketCreate, TicketUpdate).
"""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict


class ClienteDataTicket(BaseModel):
    """Datos del cliente para incluir en respuesta de ticket."""
    id: int
    nombres: str
    cedula: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None


class TicketBase(BaseModel):
    titulo: str
    descripcion: str
    cliente_id: Optional[int] = None
    estado: str = "abierto"
    prioridad: str = "media"
    tipo: str = "consulta"
    asignado_a: Optional[str] = None
    asignado_a_id: Optional[int] = None
    fecha_limite: Optional[datetime] = None
    conversacion_whatsapp_id: Optional[int] = None
    comunicacion_email_id: Optional[int] = None
    archivos: Optional[str] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    asignado_a: Optional[str] = None
    asignado_a_id: Optional[int] = None
    escalado_a_id: Optional[int] = None
    escalado: Optional[bool] = None
    fecha_limite: Optional[datetime] = None
    archivos: Optional[str] = None


class TicketResponse(BaseModel):
    """Respuesta de ticket con datos de cliente si existe."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str
    cliente_id: Optional[int] = None
    cliente: Optional[str] = None
    clienteData: Optional[ClienteDataTicket] = None
    conversacion_whatsapp_id: Optional[int] = None
    comunicacion_email_id: Optional[int] = None
    estado: str
    prioridad: str
    tipo: str
    asignado_a: Optional[str] = None
    asignado_a_id: Optional[int] = None
    escalado_a_id: Optional[int] = None
    escalado: bool = False
    fecha_limite: Optional[datetime] = None
    archivos: Optional[str] = None
    creado_por_id: Optional[int] = None
    fechaCreacion: Optional[datetime] = None
    fechaActualizacion: Optional[datetime] = None
