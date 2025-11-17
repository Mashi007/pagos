"""
Endpoints para gestionar conversaciones de WhatsApp en el CRM
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.cliente import Cliente
from app.models.user import User
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


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
        respuestas_enviadas = (
            db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.respuesta_enviada == True).count()
        )

        # Últimas 24 horas
        from datetime import datetime, timedelta

        ultimas_24h = datetime.utcnow() - timedelta(hours=24)
        ultimas_24h_count = (
            db.query(ConversacionWhatsApp).filter(ConversacionWhatsApp.timestamp >= ultimas_24h).count()
        )

        return {
            "total": total,
            "inbound": inbound,
            "outbound": outbound,
            "con_cliente": con_cliente,
            "sin_cliente": sin_cliente,
            "respuestas_enviadas": respuestas_enviadas,
            "ultimas_24h": ultimas_24h_count,
        }

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
            raise HTTPException(
                status_code=400,
                detail=resultado.get("message", "Error enviando mensaje")
            )
        
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
            f"✅ Mensaje enviado desde CRM a {numero_limpio} "
            f"(Cliente: {cliente.id if cliente else 'No encontrado'})"
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
                }
            }
        else:
            return {
                "cliente_encontrado": False,
                "cliente": None,
            }
            
    except Exception as e:
        logger.error(f"Error buscando cliente por número: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

