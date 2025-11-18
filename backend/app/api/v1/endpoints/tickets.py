"""
Endpoints para gestionar tickets de atención
Vinculados con conversaciones de WhatsApp
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, inspect, or_, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.ticket import Ticket
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _verificar_tabla_existe(db: Session) -> bool:
    """Verificar si la tabla tickets existe"""
    try:
        inspector = inspect(db.bind)
        return "tickets" in inspector.get_table_names()
    except Exception:
        return False


def _crear_tabla_si_no_existe(db: Session) -> bool:
    """Crear la tabla tickets si no existe (fallback)"""
    try:
        if _verificar_tabla_existe(db):
            return True

        logger.warning("⚠️ Tabla tickets no existe, intentando crearla...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            titulo VARCHAR(200) NOT NULL,
            descripcion TEXT NOT NULL,
            cliente_id INTEGER REFERENCES clientes(id),
            conversacion_whatsapp_id INTEGER REFERENCES conversaciones_whatsapp(id),
            estado VARCHAR(20) NOT NULL DEFAULT 'abierto',
            prioridad VARCHAR(20) NOT NULL DEFAULT 'media',
            tipo VARCHAR(20) NOT NULL DEFAULT 'consulta',
            asignado_a VARCHAR(200),
            asignado_a_id INTEGER REFERENCES users(id),
            creado_por_id INTEGER REFERENCES users(id),
            creado_en TIMESTAMP NOT NULL DEFAULT now(),
            actualizado_en TIMESTAMP NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS ix_tickets_id ON tickets(id);
        CREATE INDEX IF NOT EXISTS ix_tickets_titulo ON tickets(titulo);
        CREATE INDEX IF NOT EXISTS ix_tickets_cliente_id ON tickets(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_tickets_conversacion_whatsapp_id ON tickets(conversacion_whatsapp_id);
        CREATE INDEX IF NOT EXISTS ix_tickets_estado ON tickets(estado);
        CREATE INDEX IF NOT EXISTS ix_tickets_prioridad ON tickets(prioridad);
        CREATE INDEX IF NOT EXISTS ix_tickets_tipo ON tickets(tipo);
        CREATE INDEX IF NOT EXISTS ix_tickets_creado_en ON tickets(creado_en);
        """

        db.execute(text(create_table_sql))
        db.commit()
        logger.info("✅ Tabla tickets creada exitosamente (fallback)")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando tabla tickets (fallback): {e}", exc_info=True)
        db.rollback()
        return False


# ============================================
# SCHEMAS
# ============================================


class TicketCreate(BaseModel):
    titulo: str
    descripcion: str
    cliente_id: Optional[int] = None
    conversacion_whatsapp_id: Optional[int] = None
    comunicacion_email_id: Optional[int] = None
    estado: str = "abierto"
    prioridad: str = "media"
    tipo: str = "consulta"
    asignado_a: Optional[str] = None
    asignado_a_id: Optional[int] = None
    fecha_limite: Optional[str] = None  # ISO format datetime
    archivos: Optional[str] = None  # JSON array con rutas de archivos


class TicketUpdate(BaseModel):
    # Nota: Una vez guardado, solo se pueden actualizar estos campos (no se puede editar titulo/descripcion)
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    asignado_a: Optional[str] = None
    asignado_a_id: Optional[int] = None
    escalado_a_id: Optional[int] = None  # Escalar a admin
    escalado: Optional[bool] = None
    fecha_limite: Optional[str] = None  # ISO format datetime
    archivos: Optional[str] = None  # JSON array con rutas de archivos


class TicketResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str
    cliente_id: Optional[int]
    cliente: Optional[str]
    clienteData: Optional[dict]
    conversacion_whatsapp_id: Optional[int]
    estado: str
    prioridad: str
    tipo: str
    asignado_a: Optional[str]
    asignado_a_id: Optional[int]
    creado_por_id: Optional[int]
    fechaCreacion: Optional[str]
    fechaActualizacion: Optional[str]

    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS
# ============================================


@router.get("/tickets", response_model=dict)
async def listar_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cliente_id: Optional[int] = Query(None),
    conversacion_whatsapp_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar tickets de atención
    """
    try:
        # Verificar si la tabla existe, si no, intentar crearla
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        # Query con eager loading de la relación cliente para evitar consultas N+1
        query = db.query(Ticket).options(joinedload(Ticket.cliente))

        # Filtros
        if cliente_id:
            query = query.filter(Ticket.cliente_id == cliente_id)
        if conversacion_whatsapp_id:
            query = query.filter(Ticket.conversacion_whatsapp_id == conversacion_whatsapp_id)
        if estado:
            query = query.filter(Ticket.estado == estado)
        if prioridad:
            query = query.filter(Ticket.prioridad == prioridad)
        if tipo:
            query = query.filter(Ticket.tipo == tipo)

        # Ordenar por fecha más reciente
        query = query.order_by(Ticket.creado_en.desc())

        # Paginación
        try:
            total = query.count()
            tickets = query.offset((page - 1) * per_page).limit(per_page).all()
        except (ProgrammingError, OperationalError) as count_error:
            error_str = str(count_error).lower()
            if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
                logger.warning(f"⚠️ Error al contar tickets, intentando crear tabla: {count_error}")
                if _crear_tabla_si_no_existe(db):
                    db.refresh(Ticket)
                    query = db.query(Ticket).options(joinedload(Ticket.cliente))
                    if cliente_id:
                        query = query.filter(Ticket.cliente_id == cliente_id)
                    if conversacion_whatsapp_id:
                        query = query.filter(Ticket.conversacion_whatsapp_id == conversacion_whatsapp_id)
                    if estado:
                        query = query.filter(Ticket.estado == estado)
                    if prioridad:
                        query = query.filter(Ticket.prioridad == prioridad)
                    if tipo:
                        query = query.filter(Ticket.tipo == tipo)
                    query = query.order_by(Ticket.creado_en.desc())
                    total = query.count()
                    tickets = query.offset((page - 1) * per_page).limit(per_page).all()
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="La tabla 'tickets' no existe y no se pudo crear. Ejecuta las migraciones: alembic upgrade head",
                    )
            else:
                raise

        return {
            "tickets": [t.to_dict() for t in tickets],
            "paginacion": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    except HTTPException:
        raise
    except (ProgrammingError, OperationalError) as db_error:
        error_str = str(db_error).lower()
        if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
            logger.warning(f"⚠️ Error de base de datos, intentando crear tabla: {db_error}")
            if _crear_tabla_si_no_existe(db):
                try:
                    query = db.query(Ticket).options(joinedload(Ticket.cliente))
                    if cliente_id:
                        query = query.filter(Ticket.cliente_id == cliente_id)
                    if conversacion_whatsapp_id:
                        query = query.filter(Ticket.conversacion_whatsapp_id == conversacion_whatsapp_id)
                    if estado:
                        query = query.filter(Ticket.estado == estado)
                    if prioridad:
                        query = query.filter(Ticket.prioridad == prioridad)
                    if tipo:
                        query = query.filter(Ticket.tipo == tipo)
                    query = query.order_by(Ticket.creado_en.desc())
                    total = query.count()
                    tickets = query.offset((page - 1) * per_page).limit(per_page).all()
                    return {
                        "tickets": [t.to_dict() for t in tickets],
                        "paginacion": {
                            "page": page,
                            "per_page": per_page,
                            "total": total,
                            "pages": (total + per_page - 1) // per_page,
                        },
                    }
                except Exception:
                    pass
            raise HTTPException(
                status_code=503,
                detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
            )
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(db_error)}")
    except Exception as e:
        logger.error(f"Error listando tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/tickets", response_model=TicketResponse)
async def crear_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear un nuevo ticket de atención
    Puede estar vinculado a una conversación de WhatsApp
    """
    try:
        # Verificar si la tabla existe, si no, intentar crearla
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        # Verificar que el cliente existe si se proporciona cliente_id
        if ticket_data.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == ticket_data.cliente_id).first()
            if not cliente:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Verificar que la conversación existe si se proporciona conversacion_whatsapp_id
        if ticket_data.conversacion_whatsapp_id:
            conversacion = (
                db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.id == ticket_data.conversacion_whatsapp_id).first()
            )
            if not conversacion:
                raise HTTPException(status_code=404, detail="Conversación de WhatsApp no encontrada")

        # Verificar que la comunicación de email existe si se proporciona
        if ticket_data.comunicacion_email_id:
            from app.models.comunicacion_email import ComunicacionEmail
            comunicacion_email = (
                db.query(ComunicacionEmail).filter(ComunicacionEmail.id == ticket_data.comunicacion_email_id).first()
            )
            if not comunicacion_email:
                raise HTTPException(status_code=404, detail="Comunicación de Email no encontrada")

        # Parsear fecha_limite si se proporciona
        from datetime import datetime
        fecha_limite = None
        if ticket_data.fecha_limite:
            try:
                fecha_limite = datetime.fromisoformat(ticket_data.fecha_limite.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Error parseando fecha_limite: {e}")

        # Crear el ticket
        nuevo_ticket = Ticket(
            titulo=ticket_data.titulo,
            descripcion=ticket_data.descripcion,
            cliente_id=ticket_data.cliente_id,
            conversacion_whatsapp_id=ticket_data.conversacion_whatsapp_id,
            comunicacion_email_id=ticket_data.comunicacion_email_id,
            estado=ticket_data.estado,
            prioridad=ticket_data.prioridad,
            tipo=ticket_data.tipo,
            asignado_a=ticket_data.asignado_a or (f"{current_user.nombre} {current_user.apellido}" if current_user else None),
            asignado_a_id=ticket_data.asignado_a_id or current_user.id if current_user else None,
            fecha_limite=fecha_limite,
            archivos=ticket_data.archivos,
            creado_por_id=current_user.id if current_user else None,
        )

        db.add(nuevo_ticket)
        db.commit()
        # Refrescar con eager loading de cliente para que to_dict() funcione correctamente
        db.refresh(nuevo_ticket)
        # Cargar explícitamente la relación cliente si existe
        if nuevo_ticket.cliente_id:
            nuevo_ticket.cliente  # Esto activa la carga lazy si no está cargada

        # Si hay conversación_whatsapp_id, actualizar la conversación para vincular el ticket
        if ticket_data.conversacion_whatsapp_id:
            conversacion = (
                db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.id == ticket_data.conversacion_whatsapp_id).first()
            )
            if conversacion:
                conversacion.ticket_id = nuevo_ticket.id
                db.commit()
        
        # Si hay comunicacion_email_id, actualizar la comunicación para vincular el ticket
        if ticket_data.comunicacion_email_id:
            from app.models.comunicacion_email import ComunicacionEmail
            comunicacion_email = (
                db.query(ComunicacionEmail).filter(ComunicacionEmail.id == ticket_data.comunicacion_email_id).first()
            )
            if comunicacion_email:
                comunicacion_email.ticket_id = nuevo_ticket.id
                db.commit()

        return nuevo_ticket.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def obtener_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener un ticket específico
    """
    try:
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        ticket = db.query(Ticket).options(joinedload(Ticket.cliente)).filter(Ticket.id == ticket_id).first()

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        return ticket.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
async def actualizar_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualizar un ticket
    """
    try:
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        ticket = db.query(Ticket).options(joinedload(Ticket.cliente)).filter(Ticket.id == ticket_id).first()

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        # IMPORTANTE: Una vez guardado, NO se puede editar titulo/descripcion
        # Solo se pueden actualizar: estado, prioridad, asignación, escalación, fecha_limite, archivos
        
        # Actualizar campos permitidos
        if ticket_data.estado is not None:
            ticket.estado = ticket_data.estado
        if ticket_data.prioridad is not None:
            ticket.prioridad = ticket_data.prioridad
        if ticket_data.asignado_a is not None:
            ticket.asignado_a = ticket_data.asignado_a
        if ticket_data.asignado_a_id is not None:
            ticket.asignado_a_id = ticket_data.asignado_a_id
        
        # Escalación
        if ticket_data.escalado_a_id is not None:
            ticket.escalado_a_id = ticket_data.escalado_a_id
            ticket.escalado = True
        if ticket_data.escalado is not None:
            ticket.escalado = ticket_data.escalado
        
        # Fecha límite
        if ticket_data.fecha_limite is not None:
            from datetime import datetime
            try:
                ticket.fecha_limite = datetime.fromisoformat(ticket_data.fecha_limite.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Error parseando fecha_limite en actualización: {e}")
        
        # Archivos
        if ticket_data.archivos is not None:
            ticket.archivos = ticket_data.archivos

        # Registrar actualización en auditoría (actualizado_en se actualiza automáticamente)
        # TODO: Agregar registro específico en tabla de auditoría si existe
        
        db.commit()
        db.refresh(ticket)

        return ticket.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/tickets/conversacion/{conversacion_id}", response_model=List[TicketResponse])
async def obtener_tickets_por_conversacion(
    conversacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todos los tickets vinculados a una conversación de WhatsApp
    """
    try:
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'tickets' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        tickets = (
            db.query(Ticket)
            .options(joinedload(Ticket.cliente))
            .filter(Ticket.conversacion_whatsapp_id == conversacion_id)
            .all()
        )

        return [t.to_dict() for t in tickets]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tickets por conversación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
