# backend/app/api/v1/endpoints/notificaciones.py
"""
Endpoint para gestión de notificaciones del sistema.
Soporta Email y WhatsApp (Twilio).
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.notificacion import Notificacion, TipoNotificacion, EstadoNotificacion
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.core.config import settings
import logging

# Servicios de notificación
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas
class NotificacionCreate(BaseModel):
    cliente_id: int
    tipo: str
    canal: str  # EMAIL, WHATSAPP, SMS
    asunto: str
    mensaje: str
    programada_para: Optional[datetime] = None

class NotificacionResponse(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    canal: str
    asunto: str
    estado: str
    enviada_en: Optional[datetime]
    creada_en: datetime
    
    class Config:
        from_attributes = True

class EnvioMasivoRequest(BaseModel):
    tipo_cliente: Optional[str] = None  # MOROSO, ACTIVO, etc.
    dias_mora_min: Optional[int] = None
    template: str
    canal: str = "EMAIL"

# Servicios
email_service = EmailService()
whatsapp_service = WhatsAppService()


@router.post("/enviar", response_model=NotificacionResponse)
async def enviar_notificacion(
    notificacion: NotificacionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enviar notificación individual.
    """
    # Obtener cliente
    cliente = db.query(Cliente).filter(Cliente.id == notificacion.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Crear registro de notificación
    nueva_notif = Notificacion(
        cliente_id=notificacion.cliente_id,
        tipo=notificacion.tipo,
        canal=notificacion.canal,
        asunto=notificacion.asunto,
        mensaje=notificacion.mensaje,
        estado=EstadoNotificacion.PENDIENTE.value,
        programada_para=notificacion.programada_para or datetime.now()
    )
    
    db.add(nueva_notif)
    db.commit()
    db.refresh(nueva_notif)
    
    # Enviar en background
    if notificacion.canal == "EMAIL":
        background_tasks.add_task(
            email_service.send_email,
            to_email=cliente.email,
            subject=notificacion.asunto,
            body=notificacion.mensaje,
            notificacion_id=nueva_notif.id
        )
    elif notificacion.canal == "WHATSAPP":
        background_tasks.add_task(
            whatsapp_service.send_message,
            to_number=cliente.telefono,
            message=notificacion.mensaje,
            notificacion_id=nueva_notif.id
        )
    
    logger.info(f"Notificación {nueva_notif.id} programada para envío por {notificacion.canal}")
    return nueva_notif


@router.post("/envio-masivo")
async def envio_masivo_notificaciones(
    request: EnvioMasivoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Envío masivo de notificaciones según filtros.
    """
    # Construir query de clientes según filtros
    query = db.query(Cliente).join(Prestamo)
    
    if request.tipo_cliente == "MOROSO":
        query = query.filter(Prestamo.dias_mora > 0)
    
    if request.dias_mora_min:
        query = query.filter(Prestamo.dias_mora >= request.dias_mora_min)
    
    clientes = query.all()
    
    # Crear notificaciones masivas
    notificaciones_creadas = []
    
    for cliente in clientes:
        # Personalizar mensaje según template
        mensaje = _generar_mensaje_template(
            template=request.template,
            cliente=cliente,
            db=db
        )
        
        notif = Notificacion(
            cliente_id=cliente.id,
            tipo=TipoNotificacion.RECORDATORIO_PAGO.value,
            canal=request.canal,
            asunto=f"Recordatorio de Pago - {cliente.nombres}",
            mensaje=mensaje,
            estado=EstadoNotificacion.PENDIENTE.value,
            programada_para=datetime.now()
        )
        
        db.add(notif)
        notificaciones_creadas.append(notif)
    
    db.commit()
    
    # Programar envíos en background
    for notif in notificaciones_creadas:
        cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
        
        if request.canal == "EMAIL" and cliente.email:
            background_tasks.add_task(
                email_service.send_email,
                to_email=cliente.email,
                subject=notif.asunto,
                body=notif.mensaje,
                notificacion_id=notif.id
            )
        elif request.canal == "WHATSAPP" and cliente.telefono:
            background_tasks.add_task(
                whatsapp_service.send_message,
                to_number=cliente.telefono,
                message=notif.mensaje,
                notificacion_id=notif.id
            )
    
    return {
        "total_enviados": len(notificaciones_creadas),
        "canal": request.canal,
        "ids": [n.id for n in notificaciones_creadas]
    }


@router.get("/historial/{cliente_id}")
def historial_notificaciones(
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener historial de notificaciones de un cliente.
    """
    notificaciones = db.query(Notificacion).filter(
        Notificacion.cliente_id == cliente_id
    ).order_by(Notificacion.creada_en.desc()).all()
    
    return {
        "cliente_id": cliente_id,
        "total": len(notificaciones),
        "notificaciones": [
            {
                "id": n.id,
                "tipo": n.tipo,
                "canal": n.canal,
                "asunto": n.asunto,
                "estado": n.estado,
                "enviada_en": n.enviada_en,
                "creada_en": n.creada_en
            }
            for n in notificaciones
        ]
    }


@router.get("/pendientes")
def notificaciones_pendientes(
    db: Session = Depends(get_db)
):
    """
    Obtener notificaciones pendientes de envío.
    """
    pendientes = db.query(Notificacion).filter(
        Notificacion.estado == EstadoNotificacion.PENDIENTE.value,
        Notificacion.programada_para <= datetime.now()
    ).all()
    
    return {
        "total_pendientes": len(pendientes),
        "notificaciones": [
            {
                "id": n.id,
                "cliente_id": n.cliente_id,
                "tipo": n.tipo,
                "canal": n.canal,
                "programada_para": n.programada_para
            }
            for n in pendientes
        ]
    }


@router.post("/recordatorios-automaticos")
async def programar_recordatorios_automaticos(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Programar recordatorios automáticos para cuotas próximas a vencer.
    """
    from datetime import date
    
    # Préstamos con cuotas que vencen en los próximos 3 días
    fecha_limite = date.today() + timedelta(days=3)
    
    prestamos_proximos = db.query(Prestamo).filter(
        Prestamo.fecha_vencimiento <= fecha_limite,
        Prestamo.fecha_vencimiento >= date.today(),
        Prestamo.estado == "ACTIVO"
    ).all()
    
    recordatorios = []
    
    for prestamo in prestamos_proximos:
        mensaje = f"""
Estimado/a {prestamo.cliente.nombres},

Le recordamos que tiene una cuota próxima a vencer:
- Monto: ${prestamo.monto_cuota:,.2f}
- Fecha de vencimiento: {prestamo.fecha_vencimiento.strftime('%d/%m/%Y')}
- Días restantes: {(prestamo.fecha_vencimiento - date.today()).days}

Por favor, realice su pago a tiempo para evitar recargos.

Gracias.
        """
        
        notif = Notificacion(
            cliente_id=prestamo.cliente_id,
            tipo=TipoNotificacion.RECORDATORIO_PAGO.value,
            canal="EMAIL",
            asunto="Recordatorio: Cuota próxima a vencer",
            mensaje=mensaje,
            estado=EstadoNotificacion.PENDIENTE.value,
            programada_para=datetime.now()
        )
        
        db.add(notif)
        recordatorios.append(notif)
    
    db.commit()
    
    # Enviar en background
    for notif in recordatorios:
        cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
        if cliente.email:
            background_tasks.add_task(
                email_service.send_email,
                to_email=cliente.email,
                subject=notif.asunto,
                body=notif.mensaje,
                notificacion_id=notif.id
            )
    
    return {
        "recordatorios_programados": len(recordatorios),
        "prestamos_notificados": [p.id for p in prestamos_proximos]
    }


# Función helper para generar mensajes desde templates
def _generar_mensaje_template(template: str, cliente: Cliente, db: Session) -> str:
    """
    Generar mensaje personalizado según template.
    """
    prestamos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente.id,
        Prestamo.estado == "ACTIVO"
    ).all()
    
    if template == "RECORDATORIO_PAGO":
        total_deuda = sum(p.saldo_pendiente for p in prestamos)
        return f"""
Estimado/a {cliente.nombres} {cliente.apellidos},

Le recordamos que tiene un saldo pendiente de ${total_deuda:,.2f}.

Por favor, póngase al día con sus pagos para evitar recargos.

Gracias por su atención.
        """
    
    elif template == "MORA":
        prestamos_mora = [p for p in prestamos if p.dias_mora > 0]
        return f"""
Estimado/a {cliente.nombres},

Su cuenta presenta {len(prestamos_mora)} préstamo(s) en mora.

Por favor, comuníquese con nosotros para regularizar su situación.
        """
    
    return "Mensaje genérico de notificación."
