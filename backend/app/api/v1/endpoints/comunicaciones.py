"""
Endpoints para gestionar comunicaciones unificadas (WhatsApp y Email) en el CRM
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, inspect, or_, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.comunicacion_email import ComunicacionEmail
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class ComunicacionUnificadaResponse(BaseModel):
    """Respuesta unificada para WhatsApp y Email"""

    id: int
    tipo: str  # "whatsapp" o "email"
    from_contact: str  # from_number o from_email
    to_contact: str  # to_number o to_email
    subject: Optional[str] = None  # Solo para email
    body: Optional[str]
    timestamp: str
    direccion: str
    cliente_id: Optional[int]
    ticket_id: Optional[int]
    requiere_respuesta: bool
    procesado: bool
    respuesta_enviada: bool
    creado_en: str


class CrearClienteAutomaticoRequest(BaseModel):
    """Request para crear cliente automáticamente desde comunicación"""

    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    nombres: Optional[str] = None
    cedula: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None


# ============================================
# FUNCIONES HELPER
# ============================================


def _verificar_tabla_existe(db: Session, tabla: str) -> bool:
    """Verificar si una tabla existe"""
    try:
        inspector = inspect(db.bind)
        return tabla in inspector.get_table_names()
    except Exception:
        return False


def _buscar_o_crear_cliente(
    db: Session,
    telefono: Optional[str] = None,
    email: Optional[str] = None,
    nombres: Optional[str] = None,
    crear_automatico: bool = True,
) -> Optional[Cliente]:
    """
    Buscar cliente por teléfono o email, o crear uno nuevo si no existe

    Args:
        db: Sesión de base de datos
        telefono: Número de teléfono
        email: Email
        nombres: Nombres del cliente (para crear nuevo)
        crear_automatico: Si True, crea cliente automáticamente si no existe

    Returns:
        Cliente encontrado o creado, o None si no se puede crear
    """
    cliente = None

    # Buscar por teléfono
    if telefono:
        numero_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")
        cliente = db.query(Cliente).filter(Cliente.telefono.like(f"%{numero_limpio}%")).first()

    # Buscar por email si no se encontró
    if not cliente and email:
        cliente = db.query(Cliente).filter(Cliente.email == email).first()

    # Si no existe y se permite crear automáticamente
    if not cliente and crear_automatico:
        try:
            # Crear cliente preliminar
            nuevo_cliente = Cliente(
                cedula=nombres or f"PRELIMINAR_{datetime.utcnow().timestamp()}",
                nombres=nombres or "Cliente Preliminar",
                telefono=telefono or "0000000000",
                email=email or "preliminar@example.com",
                direccion="Pendiente de completar",
                fecha_nacimiento=datetime.utcnow().date(),
                ocupacion="Pendiente",
                estado="ACTIVO",
                activo=True,
                notas=f"Cliente creado automáticamente desde comunicación. {nombres or ''}",
                usuario_registro="sistema",
            )
            db.add(nuevo_cliente)
            db.commit()
            db.refresh(nuevo_cliente)
            logger.info(f"✅ Cliente creado automáticamente: ID {nuevo_cliente.id} ({telefono or email})")
            return nuevo_cliente
        except Exception as e:
            logger.error(f"❌ Error creando cliente automáticamente: {e}", exc_info=True)
            db.rollback()
            return None

    return cliente


# ============================================
# ENDPOINTS
# ============================================


@router.get("/comunicaciones", response_model=dict)
async def listar_comunicaciones_unificadas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tipo: Optional[str] = Query(None, description="whatsapp, email, o all"),
    cliente_id: Optional[int] = Query(None),
    requiere_respuesta: Optional[bool] = Query(None),
    direccion: Optional[str] = Query(None, description="INBOUND o OUTBOUND"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar comunicaciones unificadas (WhatsApp y Email)
    """
    try:
        comunicaciones_unificadas = []

        # Obtener comunicaciones de WhatsApp
        if not tipo or tipo == "whatsapp" or tipo == "all":
            query_whatsapp = db.query(ConversacionWhatsApp).options(joinedload(ConversacionWhatsApp.cliente))

            if cliente_id:
                query_whatsapp = query_whatsapp.filter(ConversacionWhatsApp.cliente_id == cliente_id)
            if direccion:
                query_whatsapp = query_whatsapp.filter(ConversacionWhatsApp.direccion == direccion.upper())

            # Filtrar por requiere_respuesta (INBOUND sin respuesta)
            if requiere_respuesta:
                query_whatsapp = query_whatsapp.filter(
                    and_(ConversacionWhatsApp.direccion == "INBOUND", ConversacionWhatsApp.respuesta_enviada == False)
                )

            conversaciones_whatsapp = query_whatsapp.order_by(ConversacionWhatsApp.timestamp.desc()).all()

            for conv in conversaciones_whatsapp:
                comunicaciones_unificadas.append(
                    {
                        "id": conv.id,
                        "tipo": "whatsapp",
                        "from_contact": conv.from_number,
                        "to_contact": conv.to_number,
                        "subject": None,
                        "body": conv.body,
                        "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                        "direccion": conv.direccion,
                        "cliente_id": conv.cliente_id,
                        "ticket_id": conv.ticket_id,
                        "requiere_respuesta": conv.direccion == "INBOUND" and not conv.respuesta_enviada,
                        "procesado": conv.procesado,
                        "respuesta_enviada": conv.respuesta_enviada,
                        "creado_en": conv.creado_en.isoformat() if conv.creado_en else None,
                    }
                )

        # Obtener comunicaciones de Email
        if not tipo or tipo == "email" or tipo == "all":
            if _verificar_tabla_existe(db, "comunicaciones_email"):
                query_email = db.query(ComunicacionEmail).options(joinedload(ComunicacionEmail.cliente))

                if cliente_id:
                    query_email = query_email.filter(ComunicacionEmail.cliente_id == cliente_id)
                if direccion:
                    query_email = query_email.filter(ComunicacionEmail.direccion == direccion.upper())
                if requiere_respuesta is not None:
                    query_email = query_email.filter(ComunicacionEmail.requiere_respuesta == requiere_respuesta)

                comunicaciones_email = query_email.order_by(ComunicacionEmail.timestamp.desc()).all()

                for comm in comunicaciones_email:
                    comunicaciones_unificadas.append(
                        {
                            "id": comm.id,
                            "tipo": "email",
                            "from_contact": comm.from_email,
                            "to_contact": comm.to_email,
                            "subject": comm.subject,
                            "body": comm.body,
                            "timestamp": comm.timestamp.isoformat() if comm.timestamp else None,
                            "direccion": comm.direccion,
                            "cliente_id": comm.cliente_id,
                            "ticket_id": comm.ticket_id,
                            "requiere_respuesta": comm.requiere_respuesta,
                            "procesado": comm.procesado,
                            "respuesta_enviada": comm.respuesta_enviada,
                            "creado_en": comm.creado_en.isoformat() if comm.creado_en else None,
                        }
                    )

        # Ordenar por timestamp descendente
        comunicaciones_unificadas.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        # Paginación
        total = len(comunicaciones_unificadas)
        start = (page - 1) * per_page
        end = start + per_page
        comunicaciones_paginadas = comunicaciones_unificadas[start:end]

        return {
            "comunicaciones": comunicaciones_paginadas,
            "paginacion": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    except Exception as e:
        logger.error(f"Error listando comunicaciones unificadas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/comunicaciones/crear-cliente-automatico")
async def crear_cliente_automatico(
    request: CrearClienteAutomaticoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear cliente automáticamente desde una comunicación
    """
    try:
        cliente = _buscar_o_crear_cliente(
            db=db,
            telefono=request.telefono,
            email=request.email,
            nombres=request.nombres,
            crear_automatico=True,
        )

        if not cliente:
            raise HTTPException(status_code=400, detail="No se pudo crear el cliente")

        return {
            "success": True,
            "cliente": {
                "id": cliente.id,
                "cedula": cliente.cedula,
                "nombres": cliente.nombres,
                "telefono": cliente.telefono,
                "email": cliente.email,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando cliente automático: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/comunicaciones/por-responder")
async def obtener_comunicaciones_por_responder(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener comunicaciones que requieren respuesta
    """
    return await listar_comunicaciones_unificadas(
        page=page,
        per_page=per_page,
        requiere_respuesta=True,
        direccion="INBOUND",
        db=db,
        current_user=current_user,
    )
