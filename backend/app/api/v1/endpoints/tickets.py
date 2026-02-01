"""
Endpoints de tickets CRM: conectados a BD (tabla tickets y clientes).
Al crear o actualizar ticket se notifica por correo a TICKETS_NOTIFY_EMAIL.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ticket import Ticket
from app.models.cliente import Cliente
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse, ClienteDataTicket
from app.core.email import notify_ticket_created, notify_ticket_updated
logger = logging.getLogger(__name__)
router = APIRouter()


def _ticket_to_response(t: Ticket, cliente_row: Optional[Cliente] = None) -> dict:
    """Construye respuesta de ticket con datos de cliente (camelCase para frontend)."""
    cliente_nombre = None
    cliente_data = None
    if cliente_row:
        cliente_nombre = cliente_row.nombres or ""
        cliente_data = ClienteDataTicket(
            id=cliente_row.id,
            nombres=cliente_row.nombres,
            cedula=cliente_row.cedula,
            telefono=cliente_row.telefono or None,
            email=cliente_row.email or None,
            direccion=cliente_row.direccion or None,
        )
    return {
        "id": t.id,
        "titulo": t.titulo,
        "descripcion": t.descripcion,
        "cliente_id": t.cliente_id,
        "cliente": cliente_nombre,
        "clienteData": cliente_data.model_dump() if cliente_data else None,
        "conversacion_whatsapp_id": t.conversacion_whatsapp_id,
        "comunicacion_email_id": t.comunicacion_email_id,
        "estado": t.estado,
        "prioridad": t.prioridad,
        "tipo": t.tipo,
        "asignado_a": t.asignado_a,
        "asignado_a_id": t.asignado_a_id,
        "escalado_a_id": t.escalado_a_id,
        "escalado": t.escalado or False,
        "fecha_limite": t.fecha_limite.isoformat() if t.fecha_limite else None,
        "archivos": t.archivos,
        "creado_por_id": t.creado_por_id,
        "fechaCreacion": t.fecha_creacion.isoformat() if t.fecha_creacion else None,
        "fechaActualizacion": t.fecha_actualizacion.isoformat() if t.fecha_actualizacion else None,
    }


@router.get("", summary="Listado paginado de tickets", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def get_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cliente_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de tickets desde la BD. Filtros: cliente_id, estado, prioridad, tipo."""
    q = select(Ticket)
    count_q = select(func.count()).select_from(Ticket)
    if cliente_id is not None:
        q = q.where(Ticket.cliente_id == cliente_id)
        count_q = count_q.where(Ticket.cliente_id == cliente_id)
    if estado and estado.strip():
        q = q.where(Ticket.estado == estado.strip().lower())
        count_q = count_q.where(Ticket.estado == estado.strip().lower())
    if prioridad and prioridad.strip():
        q = q.where(Ticket.prioridad == prioridad.strip().lower())
        count_q = count_q.where(Ticket.prioridad == prioridad.strip().lower())
    if tipo and tipo.strip():
        q = q.where(Ticket.tipo == tipo.strip().lower())
        count_q = count_q.where(Ticket.tipo == tipo.strip().lower())

    total = db.scalar(count_q) or 0
    q = q.order_by(Ticket.id.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).scalars().all()
    # Cargar clientes para los tickets que tienen cliente_id
    clientes_map = {}
    if rows:
        ids = [r.cliente_id for r in rows if r.cliente_id]
        if ids:
            clientes = db.execute(select(Cliente).where(Cliente.id.in_(ids))).scalars().all()
            clientes_map = {c.id: c for c in clientes}
    tickets_list = [_ticket_to_response(t, clientes_map.get(t.cliente_id)) for t in rows]
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "tickets": tickets_list,
        "paginacion": {"page": page, "per_page": per_page, "total": total, "pages": total_pages},
    }


@router.get("/{ticket_id}", response_model=dict)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Obtener un ticket por ID con datos del cliente."""
    row = db.get(Ticket, ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    cliente_row = db.get(Cliente, row.cliente_id) if row.cliente_id else None
    return _ticket_to_response(row, cliente_row)


@router.post("", response_model=dict, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    """Crear ticket en la BD y notificar por correo a TICKETS_NOTIFY_EMAIL."""
    row = Ticket(
        titulo=payload.titulo,
        descripcion=payload.descripcion,
        cliente_id=payload.cliente_id,
        estado=payload.estado or "abierto",
        prioridad=payload.prioridad or "media",
        tipo=payload.tipo or "consulta",
        asignado_a=payload.asignado_a,
        asignado_a_id=payload.asignado_a_id,
        fecha_limite=payload.fecha_limite,
        conversacion_whatsapp_id=payload.conversacion_whatsapp_id,
        comunicacion_email_id=payload.comunicacion_email_id,
        archivos=payload.archivos,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    cliente_row = db.get(Cliente, row.cliente_id) if row.cliente_id else None
    cliente_nombre = cliente_row.nombres if cliente_row else None
    notify_ticket_created(row.id, row.titulo, row.descripcion, cliente_nombre, row.prioridad)
    return _ticket_to_response(row, cliente_row)


@router.put("/{ticket_id}", response_model=dict)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    """Actualizar ticket. Notifica por correo si TICKETS_NOTIFY_EMAIL está configurado."""
    row = db.get(Ticket, ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(row)
    notify_ticket_updated(row.id, row.titulo, row.estado, row.prioridad)
    cliente_row = db.get(Cliente, row.cliente_id) if row.cliente_id else None
    return _ticket_to_response(row, cliente_row)
