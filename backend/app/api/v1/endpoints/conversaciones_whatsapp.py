"""
Endpoints para gestionar conversaciones de WhatsApp en el CRM
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


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

