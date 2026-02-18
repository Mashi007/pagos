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
    """Construye respuesta de ticket con datos de cliente (camelCase para frontend). Tolerante a NULL."""
    cliente_nombre = None
    cliente_data = None
    if cliente_row:
        cliente_nombre = (cliente_row.nombres or "").strip() or "Sin nombre"
        cliente_data = ClienteDataTicket(
            id=cliente_row.id,
            nombres=(cliente_row.nombres or "").strip() or "Sin nombre",
            cedula=(cliente_row.cedula or "").strip() or "",
            telefono=cliente_row.telefono or None,
            email=cliente_row.email or None,
            direccion=cliente_row.direccion or None,
        )
    fecha_limite = getattr(t, "fecha_limite", None)
    fecha_creacion = getattr(t, "fecha_creacion", None)
    fecha_actualizacion = getattr(t, "fecha_actualizacion", None)
    return {
        "id": t.id,
        "titulo": t.titulo or "",
        "descripcion": t.descripcion or "",
        "cliente_id": t.cliente_id,
        "cliente": cliente_nombre,
        "clienteData": cliente_data.model_dump() if cliente_data else None,
        "conversacion_whatsapp_id": t.conversacion_whatsapp_id,
        "comunicacion_email_id": t.comunicacion_email_id,
        "estado": t.estado or "abierto",
        "prioridad": t.prioridad or "media",
        "tipo": t.tipo or "consulta",
        "asignado_a": t.asignado_a,
        "asignado_a_id": t.asignado_a_id,
        "escalado_a_id": t.escalado_a_id,
        "escalado": t.escalado or False,
        "fecha_limite": fecha_limite.isoformat() if fecha_limite else None,
        "archivos": t.archivos,
        "creado_por_id": t.creado_por_id,
        "fechaCreacion": fecha_creacion.isoformat() if fecha_creacion else None,
        "fechaActualizacion": fecha_actualizacion.isoformat() if fecha_actualizacion else None,
    }


def _estadisticas_tickets(db: Session, cliente_id: Optional[int] = None) -> dict:
    """Cuenta total y por estado (abierto, en_proceso, resuelto, cerrado) desde la BD. Sin filtro estado/prioridad/tipo."""
    from sqlalchemy import case

    st = select(
        func.count().label("total"),
        func.sum(case((Ticket.estado == "abierto", 1), else_=0)).label("abiertos"),
        func.sum(case((Ticket.estado == "en_proceso", 1), else_=0)).label("en_proceso"),
        func.sum(case((Ticket.estado == "resuelto", 1), else_=0)).label("resueltos"),
        func.sum(case((Ticket.estado == "cerrado", 1), else_=0)).label("cerrados"),
    ).select_from(Ticket)
    if cliente_id is not None:
        st = st.where(Ticket.cliente_id == cliente_id)
    row = db.execute(st).first()
    if row:
        return {
            "total": row.total or 0,
            "abiertos": row.abiertos or 0,
            "en_proceso": row.en_proceso or 0,
            "resueltos": row.resueltos or 0,
            "cerrados": row.cerrados or 0,
        }
    return {"total": 0, "abiertos": 0, "en_proceso": 0, "resueltos": 0, "cerrados": 0}


def _sanitize_ticket_fks(db: Session, payload) -> dict:
    """
    Valida referencias FK y devuelve valores sanitizados.
    Si el ID no existe en la tabla referenciada, usa None.
    """
    result = {
        "asignado_a_id": None,
        "conversacion_whatsapp_id": None,
        "comunicacion_email_id": None,
        "creado_por_id": None,
        "escalado_a_id": None,
    }

    _TABLE_SQL = {
        "users": text("SELECT 1 FROM users WHERE id = :id"),
        "conversaciones_whatsapp": text("SELECT 1 FROM conversaciones_whatsapp WHERE id = :id"),
        "comunicaciones_email": text("SELECT 1 FROM comunicaciones_email WHERE id = :id"),
    }

    def _exists_in_table(table: str, id_val: int) -> bool:
        if id_val is None:
            return False
        try:
            stmt = _TABLE_SQL.get(table)
            if stmt is None:
                return False
            row = db.execute(stmt, {"id": id_val}).first()
            return row is not None
        except Exception:
            return False

    asignado_a_id = getattr(payload, "asignado_a_id", None)
    if asignado_a_id is not None:
        result["asignado_a_id"] = asignado_a_id if _exists_in_table("users", asignado_a_id) else None

    conversacion_whatsapp_id = getattr(payload, "conversacion_whatsapp_id", None)
    if conversacion_whatsapp_id is not None:
        result["conversacion_whatsapp_id"] = (
            conversacion_whatsapp_id
            if _exists_in_table("conversaciones_whatsapp", conversacion_whatsapp_id)
            else None
        )

    comunicacion_email_id = getattr(payload, "comunicacion_email_id", None)
    if comunicacion_email_id is not None:
        result["comunicacion_email_id"] = (
            comunicacion_email_id
            if _exists_in_table("comunicaciones_email", comunicacion_email_id)
            else None
        )

    creado_por_id = getattr(payload, "creado_por_id", None)
    if creado_por_id is not None:
        result["creado_por_id"] = creado_por_id if _exists_in_table("users", creado_por_id) else None

    escalado_a_id = getattr(payload, "escalado_a_id", None)
    if escalado_a_id is not None:
        result["escalado_a_id"] = escalado_a_id if _exists_in_table("users", escalado_a_id) else None

    return result


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
    """Listado paginado de tickets desde la BD. Filtros: cliente_id, estado, prioridad, tipo. Incluye estadísticas globales (KPI) por estado."""
    try:
        # Estadísticas globales (sin filtro estado/prioridad/tipo) para los KPIs
        estadisticas = _estadisticas_tickets(db, cliente_id)

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
        try:
            rows = db.execute(q).scalars().all()
        except ProgrammingError as pe:
            # BD sin fecha_creacion/fecha_actualizacion: consultar solo columnas existentes
            err_msg = str(pe)
            if "fecha_creacion" not in err_msg and "fecha_actualizacion" not in err_msg and "does not exist" not in err_msg.lower():
                raise
            db.rollback()  # transacción abortada; permitir siguiente consulta
            q_fallback = select(*_TICKET_COLUMNS_FALLBACK).select_from(Ticket)
            if cliente_id is not None:
                q_fallback = q_fallback.where(Ticket.cliente_id == cliente_id)
            if estado and estado.strip():
                q_fallback = q_fallback.where(Ticket.estado == estado.strip().lower())
            if prioridad and prioridad.strip():
                q_fallback = q_fallback.where(Ticket.prioridad == prioridad.strip().lower())
            if tipo and tipo.strip():
                q_fallback = q_fallback.where(Ticket.tipo == tipo.strip().lower())
            q_fallback = q_fallback.order_by(Ticket.id.desc()).offset((page - 1) * per_page).limit(per_page)
            rows = db.execute(q_fallback).all()
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
            "estadisticas": estadisticas,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error en listado de tickets: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar tickets: {e!s}",
        ) from e


@router.get("/{ticket_id}", response_model=dict)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Obtener un ticket por ID con datos del cliente."""
    try:
        row = db.get(Ticket, ticket_id)
    except ProgrammingError as pe:
        # BD sin fecha_creacion/fecha_actualizacion: cargar solo columnas existentes
        if "fecha_creacion" not in str(pe) and "fecha_actualizacion" not in str(pe) and "does not exist" not in str(pe).lower():
            raise
        row = db.execute(
            select(*_TICKET_COLUMNS_FALLBACK).select_from(Ticket).where(Ticket.id == ticket_id)
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if not row:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    cliente_row = db.get(Cliente, row.cliente_id) if row.cliente_id else None
    return _ticket_to_response(row, cliente_row)


@router.post("", response_model=dict, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    """Crear ticket en la BD y notificar por correo a TICKETS_NOTIFY_EMAIL."""
    try:
        fks = _sanitize_ticket_fks(db, payload)
        row = Ticket(
            titulo=payload.titulo,
            descripcion=payload.descripcion,
            cliente_id=payload.cliente_id,
            estado=payload.estado or "abierto",
            prioridad=payload.prioridad or "media",
            tipo=payload.tipo or "consulta",
            asignado_a=payload.asignado_a,
            asignado_a_id=fks["asignado_a_id"],
            fecha_limite=payload.fecha_limite,
            conversacion_whatsapp_id=fks["conversacion_whatsapp_id"],
            comunicacion_email_id=fks["comunicacion_email_id"],
            creado_por_id=fks["creado_por_id"],
            escalado_a_id=fks["escalado_a_id"],
            archivos=payload.archivos,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        cliente_row = db.get(Cliente, row.cliente_id) if row.cliente_id else None
        cliente_nombre = cliente_row.nombres if cliente_row else None
        notify_ticket_created(
            row.id,
            row.titulo,
            row.descripcion,
            cliente_nombre,
            row.prioridad or "media",
            estado=row.estado or "abierto",
            tipo=row.tipo or "consulta",
            fecha_creacion=getattr(row, "fecha_creacion", None),
        )
        return _ticket_to_response(row, cliente_row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Cliente no encontrado o referencia inválida",
        )
    except ProgrammingError:
        db.rollback()
        logger.exception("Error de base de datos al crear ticket")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al crear ticket",
        )
    except Exception as e:
        db.rollback()
        logger.exception("Error inesperado al crear ticket: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear ticket: {e!s}",
        ) from e


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

