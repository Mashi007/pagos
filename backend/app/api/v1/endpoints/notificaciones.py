from typing import Optional

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.notificacion import Notificacion
from app.models.user import User
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


# Schemas
class NotificacionCreate(BaseModel):
    cliente_id: int
    tipo: str
    canal: str  # EMAIL, WHATSAPP
    mensaje: str
    asunto: Optional[str] = None


class NotificacionResponse(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    canal: str
    mensaje: str
    asunto: Optional[str]
    estado: str
    fecha_envio: Optional[datetime]
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class EnvioMasivoRequest(BaseModel):
    tipo_cliente: str  # MOROSO, ACTIVO, etc.
    dias_mora_min: Optional[int] = None
    template: str
    canal: str = "EMAIL"


@router.post("/enviar", response_model=NotificacionResponse)
async def enviar_notificacion(
    notificacion: NotificacionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enviar notificación individual."""
    try:
        # Obtener cliente
        cliente = (
            db.query(Cliente).filter(Cliente.id == notificacion.cliente_id).first()
        )

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Crear registro de notificación
        nueva_notif = Notificacion(
            cliente_id=notificacion.cliente_id,
            tipo=notificacion.tipo,
            canal=notificacion.canal,
            mensaje=notificacion.mensaje,
            asunto=notificacion.asunto,
            estado="PENDIENTE",
        )

        db.add(nueva_notif)
        db.commit()
        db.refresh(nueva_notif)

        # Enviar según canal
        if notificacion.canal == "EMAIL":
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_email,
                to_email=cliente.email,
                subject=notificacion.asunto or "Notificación",
                body=notificacion.mensaje,
                notificacion_id=nueva_notif.id,
            )
        elif notificacion.canal == "WHATSAPP":
            whatsapp_service = WhatsAppService()
            background_tasks.add_task(
                whatsapp_service.send_message,
                phone_number=cliente.telefono,
                message=notificacion.mensaje,
                notificacion_id=nueva_notif.id,
            )

        logger.info(f"Notificación programada para cliente {cliente.id}")
        return nueva_notif

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enviando notificación: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/envio-masivo")
async def envio_masivo(
    request: EnvioMasivoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envío masivo de notificaciones."""
    try:
        # Obtener clientes según filtros
        query = db.query(Cliente).join(Prestamo, Cliente.id == Prestamo.cliente_id)

        if request.tipo_cliente == "MOROSO":
            query = query.filter(Prestamo.dias_mora > 0)

        if request.dias_mora_min:
            query = query.filter(Prestamo.dias_mora >= request.dias_mora_min)

        clientes = query.all()

        # Crear notificaciones masivas
        notificaciones_creadas = []

        for cliente in clientes:
            nueva_notif = Notificacion(
                cliente_id=cliente.id,
                tipo="MASIVA",
                canal=request.canal,
                mensaje=request.template,
                estado="PENDIENTE",
            )

            db.add(nueva_notif)
            notificaciones_creadas.append(nueva_notif)

        db.commit()

        # Programar envíos
        for notif in notificaciones_creadas:
            cliente = next(c for c in clientes if c.id == notif.cliente_id)

            if request.canal == "EMAIL":
                email_service = EmailService()
                background_tasks.add_task(
                    email_service.send_email,
                    to_email=cliente.email,
                    subject="Notificación Importante",
                    body=request.template,
                    notificacion_id=notif.id,
                )
            elif request.canal == "WHATSAPP":
                whatsapp_service = WhatsAppService()
                background_tasks.add_task(
                    whatsapp_service.send_message,
                    phone_number=cliente.telefono,
                    message=request.template,
                    notificacion_id=notif.id,
                )

        logger.info(f"Enviadas {len(notificaciones_creadas)} notificaciones masivas")

        return {
            "message": f"Enviadas {len(notificaciones_creadas)} notificaciones",
            "count": len(notificaciones_creadas),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error en envío masivo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/", response_model=list[NotificacionResponse])
def listar_notificaciones(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar notificaciones con filtros."""
    try:
        query = db.query(Notificacion)

        if estado:
            query = query.filter(Notificacion.estado == estado)

        notificaciones = query.offset(skip).limit(limit).all()
        return notificaciones

    except Exception as e:
        logger.error(f"Error listando notificaciones: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/{notificacion_id}", response_model=NotificacionResponse)
def obtener_notificacion(
    notificacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener notificación específica."""
    try:
        notificacion = (
            db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
        )

        if not notificacion:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        return notificacion

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo notificación: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/estadisticas/resumen")
def obtener_estadisticas_notificaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas de notificaciones."""
    try:
        total = db.query(Notificacion).count()
        enviadas = (
            db.query(Notificacion).filter(Notificacion.estado == "ENVIADA").count()
        )
        pendientes = (
            db.query(Notificacion).filter(Notificacion.estado == "PENDIENTE").count()
        )
        fallidas = (
            db.query(Notificacion).filter(Notificacion.estado == "FALLIDA").count()
        )

        return {
            "total": total,
            "enviadas": enviadas,
            "pendientes": pendientes,
            "fallidas": fallidas,
            "tasa_exito": (enviadas / total * 100) if total > 0 else 0,
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
