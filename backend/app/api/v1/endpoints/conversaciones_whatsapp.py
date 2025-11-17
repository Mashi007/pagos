"""
Endpoints para gestionar conversaciones de WhatsApp en el CRM
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, inspect, or_, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.user import User
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


def _verificar_tabla_existe(db: Session) -> bool:
    """Verificar si la tabla conversaciones_whatsapp existe"""
    try:
        inspector = inspect(db.bind)
        return "conversaciones_whatsapp" in inspector.get_table_names()
    except Exception:
        return False


def _crear_tabla_si_no_existe(db: Session) -> bool:
    """Crear la tabla conversaciones_whatsapp si no existe (fallback)"""
    try:
        if _verificar_tabla_existe(db):
            return True

        logger.warning("⚠️ Tabla conversaciones_whatsapp no existe, intentando crearla...")

        # Crear tabla usando SQL directo
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS conversaciones_whatsapp (
            id SERIAL PRIMARY KEY,
            message_id VARCHAR(100) UNIQUE,
            from_number VARCHAR(20) NOT NULL,
            to_number VARCHAR(20) NOT NULL,
            message_type VARCHAR(20) NOT NULL,
            body TEXT,
            timestamp TIMESTAMP NOT NULL,
            direccion VARCHAR(10) NOT NULL,
            cliente_id INTEGER REFERENCES clientes(id),
            procesado BOOLEAN NOT NULL DEFAULT false,
            respuesta_enviada BOOLEAN NOT NULL DEFAULT false,
            respuesta_id INTEGER REFERENCES conversaciones_whatsapp(id),
            respuesta_bot TEXT,
            respuesta_meta_id VARCHAR(100),
            error TEXT,
            creado_en TIMESTAMP NOT NULL DEFAULT now(),
            actualizado_en TIMESTAMP NOT NULL DEFAULT now()
        );
        
        CREATE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_id ON conversaciones_whatsapp(id);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_message_id ON conversaciones_whatsapp(message_id);
        CREATE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_from_number ON conversaciones_whatsapp(from_number);
        CREATE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_timestamp ON conversaciones_whatsapp(timestamp);
        CREATE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_cliente_id ON conversaciones_whatsapp(cliente_id);
        CREATE INDEX IF NOT EXISTS ix_conversaciones_whatsapp_creado_en ON conversaciones_whatsapp(creado_en);
        """

        db.execute(text(create_table_sql))
        db.commit()
        logger.info("✅ Tabla conversaciones_whatsapp creada exitosamente (fallback)")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando tabla conversaciones_whatsapp (fallback): {e}", exc_info=True)
        db.rollback()
        return False


class EnviarMensajeRequest(BaseModel):
    to_number: str
    message: str
    cliente_id: Optional[int] = None  # Si se proporciona, se usa directamente


@router.get("/conversaciones-whatsapp")
async def listar_conversaciones_whatsapp(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cliente_id: Optional[int] = Query(None),
    from_number: Optional[str] = Query(None),
    direccion: Optional[str] = Query(None),  # INBOUND o OUTBOUND
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar conversaciones de WhatsApp para el CRM

    Permite ver todas las conversaciones entre clientes y el bot
    """
    try:
        # Verificar si la tabla existe, si no, intentar crearla
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'conversaciones_whatsapp' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        query = db.query(ConversacionWhatsApp)

        # Filtros
        if cliente_id:
            query = query.filter(ConversacionWhatsApp.cliente_id == cliente_id)
        if from_number:
            query = query.filter(ConversacionWhatsApp.from_number.like(f"%{from_number}%"))
        if direccion:
            query = query.filter(ConversacionWhatsApp.direccion == direccion.upper())

        # Ordenar por fecha más reciente
        query = query.order_by(ConversacionWhatsApp.timestamp.desc())

        # Paginación
        total = query.count()
        conversaciones = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "conversaciones": [c.to_dict() for c in conversaciones],
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
            # Intentar crear la tabla como fallback
            if _crear_tabla_si_no_existe(db):
                # Reintentar la query
                try:
                    query = db.query(ConversacionWhatsApp)
                    if cliente_id:
                        query = query.filter(ConversacionWhatsApp.cliente_id == cliente_id)
                    if from_number:
                        query = query.filter(ConversacionWhatsApp.from_number.like(f"%{from_number}%"))
                    if direccion:
                        query = query.filter(ConversacionWhatsApp.direccion == direccion.upper())
                    query = query.order_by(ConversacionWhatsApp.timestamp.desc())
                    total = query.count()
                    conversaciones = query.offset((page - 1) * per_page).limit(per_page).all()
                    return {
                        "conversaciones": [c.to_dict() for c in conversaciones],
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
                detail="La tabla 'conversaciones_whatsapp' no existe. Ejecuta las migraciones: alembic upgrade head",
            )
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(db_error)}")
    except Exception as e:
        logger.error(f"Error listando conversaciones WhatsApp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/conversaciones-whatsapp/{conversacion_id}")
async def obtener_conversacion_whatsapp(
    conversacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener una conversación específica de WhatsApp
    """
    try:
        conversacion = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.id == conversacion_id).first()

        if not conversacion:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        return {"conversacion": conversacion.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversación WhatsApp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/conversaciones-whatsapp/cliente/{cliente_id}")
async def obtener_conversaciones_cliente(
    cliente_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todas las conversaciones de un cliente específico
    """
    try:
        query = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.cliente_id == cliente_id)

        # Ordenar por fecha más reciente
        query = query.order_by(ConversacionWhatsApp.timestamp.desc())

        # Paginación
        total = query.count()
        conversaciones = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "conversaciones": [c.to_dict() for c in conversaciones],
            "paginacion": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo conversaciones del cliente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/conversaciones-whatsapp/numero/{numero}")
async def obtener_conversaciones_numero(
    numero: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener todas las conversaciones de un número de teléfono específico
    """
    try:
        # Limpiar número
        numero_limpio = numero.replace("+", "").replace(" ", "").replace("-", "")

        query = db.query(ConversacionWhatsApp).filter(
            or_(
                ConversacionWhatsApp.from_number.like(f"%{numero_limpio}%"),
                ConversacionWhatsApp.to_number.like(f"%{numero_limpio}%"),
            )
        )

        # Ordenar por fecha más reciente
        query = query.order_by(ConversacionWhatsApp.timestamp.desc())

        # Paginación
        total = query.count()
        conversaciones = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "conversaciones": [c.to_dict() for c in conversaciones],
            "paginacion": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo conversaciones del número: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/conversaciones-whatsapp/estadisticas")
async def obtener_estadisticas_conversaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de conversaciones de WhatsApp
    """
    try:
        # Verificar si la tabla existe, si no, intentar crearla
        if not _verificar_tabla_existe(db):
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'conversaciones_whatsapp' no existe. Ejecuta las migraciones: alembic upgrade head",
                )

        from sqlalchemy import func

        # Total de conversaciones
        total = db.query(ConversacionWhatsApp).count()

        # Por dirección
        inbound = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.direccion == "INBOUND").count()
        outbound = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.direccion == "OUTBOUND").count()

        # Con cliente identificado
        con_cliente = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.cliente_id.isnot(None)).count()
        sin_cliente = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.cliente_id.is_(None)).count()

        # Respuestas enviadas
        respuestas_enviadas = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.respuesta_enviada == True).count()

        # Últimas 24 horas
        from datetime import datetime, timedelta

        ultimas_24h = datetime.utcnow() - timedelta(hours=24)
        ultimas_24h_count = db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.timestamp >= ultimas_24h).count()

        return {
            "total": total,
            "inbound": inbound,
            "outbound": outbound,
            "con_cliente": con_cliente,
            "sin_cliente": sin_cliente,
            "respuestas_enviadas": respuestas_enviadas,
            "ultimas_24h": ultimas_24h_count,
        }

    except HTTPException:
        raise
    except (ProgrammingError, OperationalError) as db_error:
        error_str = str(db_error).lower()
        if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
            if not _crear_tabla_si_no_existe(db):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'conversaciones_whatsapp' no existe. Ejecuta las migraciones: alembic upgrade head",
                )
            # Si se creó, retornar estadísticas vacías
            return {
                "total": 0,
                "inbound": 0,
                "outbound": 0,
                "con_cliente": 0,
                "sin_cliente": 0,
                "respuestas_enviadas": 0,
                "ultimas_24h": 0,
            }
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(db_error)}")
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/conversaciones-whatsapp/enviar-mensaje")
async def enviar_mensaje_desde_crm(
    request: EnviarMensajeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enviar mensaje de WhatsApp desde el CRM

    Si el cliente no existe, se puede crear primero usando el endpoint de clientes.
    Este endpoint busca el cliente por número de teléfono o por cliente_id.
    """
    try:
        from app.services.whatsapp_service import WhatsAppService

        whatsapp_service = WhatsAppService(db=db)

        # Limpiar número de teléfono
        numero_limpio = request.to_number.replace("+", "").replace(" ", "").replace("-", "")

        # Buscar cliente
        cliente = None
        if request.cliente_id:
            # Si se proporciona cliente_id, usarlo directamente
            cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
        else:
            # Buscar por número de teléfono
            cliente = db.query(Cliente).filter(Cliente.telefono.like(f"%{numero_limpio}%")).first()

        # Enviar mensaje
        resultado = await whatsapp_service.send_message(
            to_number=numero_limpio,
            message=request.message,
        )

        if not resultado.get("success"):
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error enviando mensaje"))

        # Guardar mensaje en BD
        conversacion_outbound = ConversacionWhatsApp(
            message_id=resultado.get("message_id"),
            from_number=whatsapp_service.phone_number_id,
            to_number=numero_limpio,
            message_type="text",
            body=request.message,
            timestamp=datetime.utcnow(),
            direccion="OUTBOUND",
            cliente_id=cliente.id if cliente else None,
            procesado=True,
            respuesta_enviada=True,
            respuesta_meta_id=resultado.get("message_id"),
        )
        db.add(conversacion_outbound)
        db.commit()
        db.refresh(conversacion_outbound)

        logger.info(
            f"✅ Mensaje enviado desde CRM a {numero_limpio} " f"(Cliente: {cliente.id if cliente else 'No encontrado'})"
        )

        return {
            "success": True,
            "conversacion": conversacion_outbound.to_dict(),
            "cliente_encontrado": cliente is not None,
            "cliente_id": cliente.id if cliente else None,
            "message_id": resultado.get("message_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enviando mensaje desde CRM: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/conversaciones-whatsapp/buscar-cliente/{numero}")
async def buscar_cliente_por_numero(
    numero: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Buscar cliente por número de teléfono

    Retorna información del cliente si existe, o null si no existe.
    Útil para determinar si se debe crear un cliente nuevo.
    """
    try:
        # Limpiar número
        numero_limpio = numero.replace("+", "").replace(" ", "").replace("-", "")

        # Buscar cliente
        cliente = db.query(Cliente).filter(Cliente.telefono.like(f"%{numero_limpio}%")).first()

        if cliente:
            return {
                "cliente_encontrado": True,
                "cliente": {
                    "id": cliente.id,
                    "cedula": cliente.cedula,
                    "nombres": cliente.nombres,
                    "telefono": cliente.telefono,
                    "email": cliente.email,
                },
            }
        else:
            return {
                "cliente_encontrado": False,
                "cliente": None,
            }

    except Exception as e:
        logger.error(f"Error buscando cliente por número: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
