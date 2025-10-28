import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.notificacion_plantilla import NotificacionPlantilla
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.notificacion_plantilla import (
    NotificacionPlantillaCreate,
    NotificacionPlantillaResponse,
    NotificacionPlantillaUpdate,
)
from app.services.email_service import EmailService
from app.services.notificacion_automatica_service import (
    NotificacionAutomaticaService,
)
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
                to_emails=[str(cliente.email)],
                subject=notificacion.asunto or "Notificación",
                body=notificacion.mensaje,
            )
        elif notificacion.canal == "WHATSAPP":
            whatsapp_service = WhatsAppService()
            background_tasks.add_task(
                whatsapp_service.send_message,
                to_number=str(cliente.telefono),
                message=notificacion.mensaje,
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
                    to_emails=[str(cliente.email)],
                    subject="Notificación Importante",
                    body=request.template,
                )
            elif request.canal == "WHATSAPP":
                whatsapp_service = WhatsAppService()
                background_tasks.add_task(
                    whatsapp_service.send_message,
                    to_number=str(cliente.telefono),
                    message=request.template,
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


# ============================================
# PLANTILLAS DE NOTIFICACIONES
# ============================================


@router.get("/plantillas", response_model=list[NotificacionPlantillaResponse])
def listar_plantillas(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    solo_activas: bool = Query(True, description="Solo plantillas activas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar plantillas de notificaciones"""
    try:
        query = db.query(NotificacionPlantilla)

        if solo_activas:
            query = query.filter(NotificacionPlantilla.activa == True)

        if tipo:
            query = query.filter(NotificacionPlantilla.tipo == tipo)

        plantillas = query.order_by(NotificacionPlantilla.nombre).all()
        return plantillas

    except Exception as e:
        logger.error(f"Error listando plantillas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/plantillas", response_model=NotificacionPlantillaResponse)
def crear_plantilla(
    plantilla: NotificacionPlantillaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear nueva plantilla de notificación"""
    try:
        # Verificar si ya existe una plantilla con el mismo nombre
        existe = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.nombre == plantilla.nombre)
            .first()
        )
        if existe:
            raise HTTPException(
                status_code=400, detail="Ya existe una plantilla con este nombre"
            )

        nueva_plantilla = NotificacionPlantilla(**plantilla.model_dump())
        db.add(nueva_plantilla)
        db.commit()
        db.refresh(nueva_plantilla)

        return nueva_plantilla

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/plantillas/{plantilla_id}", response_model=NotificacionPlantillaResponse)
def actualizar_plantilla(
    plantilla_id: int,
    plantilla: NotificacionPlantillaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar plantilla de notificación"""
    try:
        plantilla_existente = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.id == plantilla_id)
            .first()
        )

        if not plantilla_existente:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        # Actualizar solo campos proporcionados
        update_data = plantilla.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plantilla_existente, key, value)

        db.commit()
        db.refresh(plantilla_existente)

        return plantilla_existente

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/plantillas/{plantilla_id}")
def eliminar_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar plantilla de notificación"""
    try:
        plantilla = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.id == plantilla_id)
            .first()
        )

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        db.delete(plantilla)
        db.commit()

        return {"mensaje": "Plantilla eliminada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/plantillas/{plantilla_id}", response_model=NotificacionPlantillaResponse)
def obtener_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener plantilla específica"""
    try:
        plantilla = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.id == plantilla_id)
            .first()
        )

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        return plantilla

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/plantillas/{plantilla_id}/enviar")
async def enviar_notificacion_con_plantilla(
    plantilla_id: int,
    cliente_id: int,
    variables: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enviar notificación usando una plantilla"""
    try:
        # Obtener plantilla
        plantilla = (
            db.query(NotificacionPlantilla)
            .filter(NotificacionPlantilla.id == plantilla_id)
            .first()
        )

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        if not plantilla.activa:
            raise HTTPException(status_code=400, detail="La plantilla no está activa")

        # Obtener cliente
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Reemplazar variables en el asunto y cuerpo
        asunto = plantilla.asunto
        cuerpo = plantilla.cuerpo

        for key, value in variables.items():
            asunto = asunto.replace(f"{{{{{key}}}}}", str(value))
            cuerpo = cuerpo.replace(f"{{{{{key}}}}}", str(value))

        # Crear registro de notificación
        nueva_notif = Notificacion(
            cliente_id=cliente_id,
            tipo=plantilla.tipo,
            mensaje=cuerpo,
            estado="PENDIENTE",
        )
        db.add(nueva_notif)
        db.commit()
        db.refresh(nueva_notif)

        # Enviar email en background
        if cliente.email:
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_email,
                to_emails=[str(cliente.email)],
                subject=asunto,
                body=cuerpo,
                is_html=True,
            )

        logger.info(f"Notificación enviada usando plantilla {plantilla_id}")

        return {
            "mensaje": "Notificación enviada",
            "cliente_id": cliente_id,
            "asunto": asunto,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enviando notificación con plantilla: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
