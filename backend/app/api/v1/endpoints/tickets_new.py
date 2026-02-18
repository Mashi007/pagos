"""
Endpoints de tickets CRM: conectados a BD (tabla tickets y clientes).
Al crear o actualizar ticket se notifica por correo a TICKETS_NOTIFY_EMAIL.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.deps import get_current_user
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.core.database import get_db
from app.models.ticket import Ticket
from app.models.cliente import Cliente
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse, ClienteDataTicket
from app.core.email import notify_ticket_created, notify_ticket_updated
logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


# Columnas de Ticket sin fecha_creacion/fecha_actualizacion (fallback si la BD no tiene esas columnas)
_TICKET_COLUMNS_FALLBACK = (
    Ticket.id, Ticket.titulo, Ticket.descripcion, Ticket.cliente_id, Ticket.estado,
    Ticket.prioridad, Ticket.tipo, Ticket.asignado_a, Ticket.asignado_a_id,
    Ticket.escalado_a_id, Ticket.escalado, Ticket.fecha_limite,
    Ticket.conversacion_whatsapp_id, Ticket.comunicacion_email_id, Ticket.creado_por_id,
    Ticket.archivos,
)


def _ticket_to_response(t, cliente_row: Optional[Cliente] = None) -> dict:
