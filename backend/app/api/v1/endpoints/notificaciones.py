# backend/app/api/v1/endpoints/notificaciones.py
"""
Endpoint para gestión de notificaciones del sistema.
Soporta Email y WhatsApp (Twilio).
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.notificacion import Notificacion
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from decimal import Decimal
from app.models.analista import Analista
import logging

# Servicios de notificación
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService
from app.api.deps import get_current_user
from app.models.user import User

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
    categoria: str
    asunto: str
    estado: str
    enviada_en: Optional[datetime]
    creado_en: datetime

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
        tipo=notificacion.canal,  # EMAIL, WHATSAPP, SMS
        categoria="RECORDATORIO_PAGO",
        asunto=notificacion.asunto,
        mensaje=notificacion.mensaje,
        estado="PENDIENTE",
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
            tipo=request.canal,
            categoria="RECORDATORIO_PAGO",
            asunto=f"Recordatorio de Pago - {cliente.nombres}",
            mensaje=mensaje,
            estado="PENDIENTE",
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
    ).order_by(Notificacion.creado_en.desc()).all()

    return {
        "cliente_id": cliente_id,
        "total": len(notificaciones),
        "notificaciones": [
            {
                "id": n.id,
                "tipo": n.tipo,
                "categoria": n.categoria,
                "asunto": n.asunto,
                "estado": n.estado,
                "enviada_en": n.enviada_en,
                "creado_en": n.creado_en
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
        Notificacion.estado == "PENDIENTE",
        Notificacion.programada_para <= datetime.now()
    ).all()

    return {
        "total_pendientes": len(pendientes),
        "notificaciones": [
            {
                "id": n.id,
                "cliente_id": n.cliente_id,
                "tipo": n.tipo,
                "categoria": n.categoria,
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
            tipo="EMAIL",
            categoria="RECORDATORIO_PAGO",
            asunto="Recordatorio: Cuota próxima a vencer",
            mensaje=mensaje,
            estado="PENDIENTE",
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


# ============================================
# NOTIFICACIONES AUTOMÁTICAS PROGRAMADAS
# ============================================

@router.post("/programar-automaticas")
async def programar_notificaciones_automaticas(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Programar todas las notificaciones automáticas del sistema
    Debe ejecutarse diariamente via cron job
    """
    from datetime import date

    notificaciones_programadas = []

    # 1. RECORDATORIOS PRE-VENCIMIENTO (3 días antes)
    fecha_recordatorio = date.today() + timedelta(days=3)

    cuotas_proximas = db.query(Cuota).join(Prestamo).join(Cliente).filter(
        Cuota.fecha_vencimiento == fecha_recordatorio,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"]),
        Cliente.email.isnot(None),
        Cliente.activo == True
    ).all()

    for cuota in cuotas_proximas:
        cliente = cuota.prestamo.cliente

        # Verificar que no se haya enviado ya
        ya_enviado = db.query(Notificacion).filter(
            Notificacion.cliente_id == cliente.id,
            Notificacion.categoria == "CUOTA_PROXIMA",
            func.date(Notificacion.creado_en) == date.today()
        ).first()

        if not ya_enviado:
            mensaje = f"""
Estimado/a {cliente.nombre_completo},

Le recordamos que tiene una cuota próxima a vencer:

• Cuota #: {cuota.numero_cuota}
• Monto: ${float(cuota.monto_cuota):,.2f}
• Fecha de vencimiento: {cuota.fecha_vencimiento.strftime('%d/%m/%Y')}
• Días restantes: 3

Por favor, realice su pago a tiempo para evitar recargos por mora.

Instrucciones de pago:
- Transferencia bancaria: Cuenta 123456789
- Efectivo: En nuestras oficinas
- Referencia: CUOTA-{cuota.id}

Datos de contacto:
Teléfono: (021) 123-456
Email: cobranzas@financiera.com

Gracias por su puntualidad.
            """

            notif = Notificacion(
                cliente_id=cliente.id,
                tipo="EMAIL",
                categoria="CUOTA_PROXIMA",
                asunto=f"Recordatorio: Cuota #{cuota.numero_cuota} vence en 3 días",
                mensaje=mensaje,
                estado="PENDIENTE",
                programada_para=datetime.now().replace(hour=9, minute=0, second=0),
                prioridad="ALTA"
            )

            db.add(notif)
            notificaciones_programadas.append(notif)

    # 2. AVISOS DE CUOTA VENCIDA (día siguiente)
    cuotas_vencidas_ayer = db.query(Cuota).join(Prestamo).join(Cliente).filter(
        Cuota.fecha_vencimiento == date.today() - timedelta(days=1),
        Cuota.estado.in_(["VENCIDA", "PARCIAL"]),
        Cliente.email.isnot(None),
        Cliente.activo == True
    ).all()

    for cuota in cuotas_vencidas_ayer:
        cliente = cuota.prestamo.cliente

        # Calcular mora
        mora_calculada = cuota.calcular_mora(Decimal(str(settings.TASA_MORA_DIARIA)))

        mensaje = f"""
Estimado/a {cliente.nombre_completo},

ALERTA: Su cuota #{cuota.numero_cuota} está VENCIDA.

• Fecha de vencimiento: {cuota.fecha_vencimiento.strftime('%d/%m/%Y')}
• Días de mora: {(date.today() - cuota.fecha_vencimiento).days}
• Monto adeudado: ${float(cuota.monto_pendiente_total):,.2f}
• Recargo por mora: ${float(mora_calculada):,.2f}

URGENTE: Regularice su pago inmediatamente para evitar:
- Incremento de mora diaria
- Reporte en centrales de riesgo
- Acciones legales

Contacto inmediato: (021) 123-456
        """

        notif = Notificacion(
            cliente_id=cliente.id,
            tipo="EMAIL",
            categoria="CUOTA_VENCIDA",
            asunto=f"🔴 URGENTE: Cuota #{cuota.numero_cuota} VENCIDA",
            mensaje=mensaje,
            estado="PENDIENTE",
            programada_para=datetime.now(),
            prioridad="URGENTE"
        )

        db.add(notif)
        notificaciones_programadas.append(notif)

    db.commit()

    # Programar envíos
    for notif in notificaciones_programadas:
        cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
        if cliente.email:
            background_tasks.add_task(
                email_service.send_template_email,
                to_email=cliente.email,
                subject=notif.asunto,
                template_name="recordatorio_pago" if "recordatorio" in notif.asunto.lower() else "mora",
                context={
                    "cliente_nombre": cliente.nombre_completo,
                    "empresa": "Financiera Automotriz",
                    "telefono": "(021) 123-456",
                    "email": "info@financiera.com"
                },
                notificacion_id=notif.id
            )

    return {
        "notificaciones_programadas": len(notificaciones_programadas),
        "recordatorios_pre_vencimiento": len([n for n in notificaciones_programadas if n.categoria == "CUOTA_PROXIMA"]),
        "avisos_vencidas": len([n for n in notificaciones_programadas if n.categoria == "CUOTA_VENCIDA"])
    }


@router.post("/confirmar-pago-recibido/{pago_id}")
async def enviar_confirmacion_pago(
    pago_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    3. Confirmación de pago recibido (automática al registrar pago)
    """
    # Obtener pago con joins explícitos
    pago = db.query(Pago).select_from(Pago).join(
        Prestamo, Pago.prestamo_id == Prestamo.id
    ).join(
        Cliente, Prestamo.cliente_id == Cliente.id
    ).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    cliente = pago.prestamo.cliente

    # Calcular próximo vencimiento
    proxima_cuota = db.query(Cuota).filter(
        Cuota.prestamo_id == pago.prestamo_id,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
    ).order_by(Cuota.numero_cuota).first()

    proximo_vencimiento = "No hay cuotas pendientes"
    if proxima_cuota:
        proximo_vencimiento = f"Cuota #{proxima_cuota.numero_cuota} - {proxima_cuota.fecha_vencimiento.strftime('%d/%m/%Y')}"

    mensaje = f"""
Estimado/a {cliente.nombre_completo},

¡Gracias por su pago!

CONFIRMACIÓN DE PAGO RECIBIDO:
• Fecha: {pago.fecha_pago.strftime('%d/%m/%Y')}
• Monto: ${float(pago.monto_pagado):,.2f}
• Cuota(s) pagada(s): #{pago.numero_cuota}
• Método: {pago.metodo_pago}
• Referencia: {pago.numero_operacion or pago.comprobante or 'N/A'}

DETALLE DE APLICACIÓN:
• Capital: ${float(pago.monto_capital):,.2f}
• Interés: ${float(pago.monto_interes):,.2f}
• Mora: ${float(pago.monto_mora):,.2f}

ESTADO ACTUAL:
• Saldo pendiente: ${float(pago.prestamo.saldo_pendiente):,.2f}
• Próximo vencimiento: {proximo_vencimiento}

Agradecemos su puntualidad y confianza.
    """

    # Crear notificación
    notif = Notificacion(
        cliente_id=cliente.id,
        tipo="EMAIL",
        categoria="PAGO_RECIBIDO",
        asunto=f"✅ Confirmación: Pago de ${float(pago.monto_pagado):,.2f} recibido",
        mensaje=mensaje,
        estado="PENDIENTE",
        programada_para=datetime.now(),
        prioridad="NORMAL"
    )

    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Enviar inmediatamente
    if cliente.email:
        background_tasks.add_task(
            email_service.send_email,
            to_email=cliente.email,
            subject=notif.asunto,
            body=notif.mensaje,
            notificacion_id=notif.id
        )

    return {
        "message": "Confirmación de pago programada",
        "notificacion_id": notif.id,
        "cliente": cliente.nombre_completo
    }


@router.post("/estado-cuenta-mensual")
async def enviar_estados_cuenta_mensual(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    4. Estado de cuenta mensual (primer día de cada mes)
    """
    # Obtener todos los clientes activos con email
    clientes = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.email.isnot(None)
    ).all()

    estados_enviados = []

    for cliente in clientes:
        # Calcular resumen del mes anterior
        mes_anterior = date.today().replace(day=1) - timedelta(days=1)
        inicio_mes = mes_anterior.replace(day=1)
        fin_mes = mes_anterior

        # Pagos del mes anterior con joins explícitos
        pagos_mes = db.query(Pago).select_from(Pago).join(
            Prestamo, Pago.prestamo_id == Prestamo.id
        ).filter(
            Prestamo.cliente_id == cliente.id,
            Pago.fecha_pago >= inicio_mes,
            Pago.fecha_pago <= fin_mes
        ).all()

        # Cuotas pendientes con joins explícitos
        cuotas_pendientes = db.query(Cuota).select_from(Cuota).join(
            Prestamo, Cuota.prestamo_id == Prestamo.id
        ).filter(
            Prestamo.cliente_id == cliente.id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"])
        ).order_by(Cuota.fecha_vencimiento).limit(3).all()

        # Resumen financiero
        resumen = cliente.calcular_resumen_financiero(db)

        mensaje = f"""
Estimado/a {cliente.nombre_completo},

ESTADO DE CUENTA - {mes_anterior.strftime('%B %Y').upper()}

RESUMEN DEL MES ANTERIOR:
• Pagos realizados: {len(pagos_mes)}
• Total pagado: ${sum(float(p.monto_pagado) for p in pagos_mes):,.2f}

ESTADO ACTUAL:
• Total financiado: ${float(resumen['total_financiado']):,.2f}
• Total pagado: ${float(resumen['total_pagado']):,.2f}
• Saldo pendiente: ${float(resumen['saldo_pendiente']):,.2f}
• Cuotas pagadas: {resumen['cuotas_pagadas']} / {resumen['cuotas_totales']}
• % Avance: {resumen['porcentaje_avance']}%

PRÓXIMOS VENCIMIENTOS:
"""

        for cuota in cuotas_pendientes:
            mensaje += f"• Cuota #{cuota.numero_cuota}: ${float(cuota.monto_cuota):,.2f} - {cuota.fecha_vencimiento.strftime('%d/%m/%Y')}\n"

        mensaje += "\nMantengase al día con sus pagos.\n\nSaludos cordiales."

        # Crear notificación
        notif = Notificacion(
            cliente_id=cliente.id,
            tipo="EMAIL",
            categoria="GENERAL",
            asunto=f"Estado de Cuenta - {mes_anterior.strftime('%B %Y')}",
            mensaje=mensaje,
            estado="PENDIENTE",
            programada_para=datetime.now().replace(hour=10, minute=0),
            prioridad="NORMAL"
        )

        db.add(notif)
        estados_enviados.append(notif)

    db.commit()

    # Programar envíos
    for notif in estados_enviados:
        cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
        background_tasks.add_task(
            email_service.send_email,
            to_email=cliente.email,
            subject=notif.asunto,
            body=notif.mensaje,
            notificacion_id=notif.id
        )

    return {
        "estados_cuenta_programados": len(estados_enviados),
        "clientes_notificados": [c.id for c in clientes]
    }


# ============================================
# NOTIFICACIONES A USUARIOS DEL SISTEMA
# ============================================

@router.post("/usuarios/resumen-diario")
async def enviar_resumen_diario_usuarios(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🔔 Notificaciones diarias a usuarios (8:00 AM):
    - Resumen de vencimientos del día
    - Pagos recibidos ayer
    - Clientes que entraron en mora
    - Alertas de clientes críticos (>30 días mora)
    """
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # Obtener datos del día
    vencimientos_hoy = db.query(Cuota).join(Prestamo).join(Cliente).filter(
        Cuota.fecha_vencimiento == hoy,
        Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
    ).count()

    pagos_ayer = db.query(Pago).filter(
        Pago.fecha_pago == ayer,
        Pago.estado != "ANULADO"
    ).all()

    total_cobrado_ayer = sum(float(p.monto_pagado) for p in pagos_ayer)

    # Clientes que entraron en mora ayer
    nuevos_morosos = db.query(Cliente).join(Prestamo).join(Cuota).filter(
        Cuota.fecha_vencimiento == ayer,
        Cuota.estado == "VENCIDA",
        Cliente.activo == True
    ).distinct().all()

    # Clientes críticos (>30 días mora)
    clientes_criticos = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.dias_mora > 30
    ).count()

    # Obtener usuarios para notificar
    usuarios_notificar = db.query(User).filter(
        User.is_admin == True,
        User.is_active == True,
        User.email.isnot(None)
    ).all()

    for usuario in usuarios_notificar:
        mensaje = f"""
Buenos días {usuario.full_name},

RESUMEN DIARIO - {hoy.strftime('%d/%m/%Y')}

📅 VENCIMIENTOS HOY: {vencimientos_hoy} cuotas
💰 COBRADO AYER: ${total_cobrado_ayer:,.2f} ({len(pagos_ayer)} pagos)
⚠️ NUEVOS MOROSOS: {len(nuevos_morosos)} clientes
🚨 CLIENTES CRÍTICOS: {clientes_criticos} (>30 días mora)

ACCIONES RECOMENDADAS:
• Contactar clientes con vencimientos hoy
• Seguimiento a nuevos morosos
• Atención prioritaria a clientes críticos

Acceder al sistema: https://pagos-f2qf.onrender.com

Saludos.
        """

        notif = Notificacion(
            user_id=usuario.id,
            tipo="EMAIL",
            categoria="GENERAL",
            asunto=f"📊 Resumen Diario - {hoy.strftime('%d/%m/%Y')}",
            mensaje=mensaje,
            estado="PENDIENTE",
            programada_para=datetime.now().replace(hour=8, minute=0),
            prioridad="NORMAL"
        )

        db.add(notif)

        # Enviar
        background_tasks.add_task(
            email_service.send_email,
            to_email=usuario.email,
            subject=notif.asunto,
            body=notif.mensaje,
            notificacion_id=notif.id
        )

    db.commit()

    return {
        "usuarios_notificados": len(usuarios_notificar),
        "vencimientos_hoy": vencimientos_hoy,
        "total_cobrado_ayer": total_cobrado_ayer,
        "nuevos_morosos": len(nuevos_morosos),
        "clientes_criticos": clientes_criticos
    }


@router.post("/usuarios/reporte-semanal")
async def enviar_reporte_semanal_usuarios(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🔔 Notificaciones semanales (Lunes 9:00 AM):
    - Reporte semanal de cobranza
    - Nuevos clientes de la semana
    - Evolución de la cartera
    - Top performers y alertas
    """
    # Calcular semana anterior (lunes a domingo)
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday() + 7)  # Lunes semana anterior
    fin_semana = inicio_semana + timedelta(days=6)  # Domingo semana anterior

    # Datos de la semana
    pagos_semana = db.query(Pago).filter(
        Pago.fecha_pago >= inicio_semana,
        Pago.fecha_pago <= fin_semana,
        Pago.estado != "ANULADO"
    ).all()

    nuevos_clientes = db.query(Cliente).filter(
        func.date(Cliente.fecha_registro) >= inicio_semana,
        func.date(Cliente.fecha_registro) <= fin_semana
    ).all()

    # Top analista de la semana
    top_analista = db.query(
        User.full_name,
        func.count(Cliente.id).label('nuevos_clientes')
    ).outerjoin(Cliente, and_(
        Analista.id == Cliente.analista_id,
        func.date(Cliente.fecha_registro) >= inicio_semana,
        func.date(Cliente.fecha_registro) <= fin_semana
    )).filter(
        User.is_admin == False,
    ).group_by(User.id, User.full_name).order_by(
        func.count(Cliente.id).desc()
    ).first()

    # Enviar a usuarios gerenciales
    usuarios_gerenciales = db.query(User).filter(
        User.is_admin == True,
        User.is_active == True,
        User.email.isnot(None)
    ).all()

    for usuario in usuarios_gerenciales:
        mensaje = f"""
Buenos días {usuario.full_name},

REPORTE SEMANAL - {inicio_semana.strftime('%d/%m')} al {fin_semana.strftime('%d/%m/%Y')}

📊 COBRANZA:
• Total cobrado: ${sum(float(p.monto_pagado) for p in pagos_semana):,.2f}
• Número de pagos: {len(pagos_semana)}
• Promedio por pago: ${(sum(float(p.monto_pagado) for p in pagos_semana) / len(pagos_semana)):,.2f if pagos_semana else 0}

👥 NUEVOS CLIENTES: {len(nuevos_clientes)}

🏆 TOP PERFORMER: {top_analista[0] if top_analista else 'N/A'} ({top_analista[1] if top_analista else 0} nuevos clientes)

📈 EVOLUCIÓN DE CARTERA:
• Clientes activos: {db.query(Cliente).filter(Cliente.activo == True).count()}
• Tasa de morosidad: {db.query(Cliente).filter(Cliente.dias_mora > 0).count() / db.query(Cliente).filter(Cliente.activo == True).count() * 100:.2f}%

Revisar dashboard completo: https://pagos-f2qf.onrender.com

Saludos.
        """

        notif = Notificacion(
            user_id=usuario.id,
            tipo="EMAIL",
            categoria="GENERAL",
            asunto=f"📈 Reporte Semanal - {inicio_semana.strftime('%d/%m')} al {fin_semana.strftime('%d/%m')}",
            mensaje=mensaje,
            estado="PENDIENTE",
            programada_para=datetime.now().replace(hour=9, minute=0),
            prioridad="NORMAL"
        )

        db.add(notif)

        background_tasks.add_task(
            email_service.send_email,
            to_email=usuario.email,
            subject=notif.asunto,
            body=notif.mensaje,
            notificacion_id=notif.id
        )

    db.commit()

    return {
        "usuarios_notificados": len(usuarios_gerenciales),
        "nuevos_clientes_semana": len(nuevos_clientes),
        "total_cobrado_semana": sum(float(p.monto_pagado) for p in pagos_semana)
    }


# ============================================
# CONFIGURACIÓN DE NOTIFICACIONES
# ============================================

@router.get("/configuracion")
def obtener_configuracion_notificaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ Obtener configuración de notificaciones
    """
    return {
        "notificaciones_habilitadas": {
            "recordatorios_pre_vencimiento": True,
            "avisos_cuota_vencida": True,
            "confirmacion_pago": True,
            "estado_cuenta_mensual": True,
            "resumen_diario_usuarios": True,
            "reporte_semanal": True,
            "reporte_mensual": True
        },
        "configuracion_horarios": {
            "recordatorios_clientes": "09:00",
            "resumen_diario": "08:00",
            "reporte_semanal": "09:00",  # Lunes
            "reporte_mensual": "10:00"   # Día 1
        },
        "configuracion_frecuencias": {
            "dias_anticipacion_recordatorio": 3,
            "frecuencia_recordatorios_mora": 3,  # cada 3 días
            "max_intentos_envio": 3
        },
        "plantillas_disponibles": [
            "recordatorio_pago",
            "cuota_vencida", 
            "pago_recibido",
            "estado_cuenta",
            "mora",
            "prestamo_aprobado"
        ],
        "configuracion_smtp": {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "habilitado": settings.EMAIL_ENABLED,
            "from_name": settings.FROM_NAME
        }
    }


@router.get("/historial-completo")
def historial_completo_notificaciones(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    tipo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Historial completo de notificaciones
    - Log completo de emails enviados
    - Estado: Enviado/Entregado/Rebotado/Error
    - Filtros por cliente, tipo, fecha
    """
    query = db.query(Notificacion).select_from(Notificacion).outerjoin(Cliente).outerjoin(User)

    # Aplicar filtros
    if fecha_desde:
        query = query.filter(func.date(Notificacion.creado_en) >= fecha_desde)

    if fecha_hasta:
        query = query.filter(func.date(Notificacion.creado_en) <= fecha_hasta)

    if tipo:
        query = query.filter(Notificacion.tipo == tipo)

    if estado:
        query = query.filter(Notificacion.estado == estado)

    if cliente_id:
        query = query.filter(Notificacion.cliente_id == cliente_id)

    # Paginación
    total = query.count()
    skip = (page - 1) * page_size
    notificaciones = query.order_by(Notificacion.creado_en.desc()).offset(skip).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "notificaciones": [
            {
                "id": n.id,
                "destinatario": n.cliente.nombre_completo if n.cliente else (n.user.full_name if n.user else "N/A"),
                "tipo": n.tipo.value,
                "categoria": n.categoria.value,
                "asunto": n.asunto,
                "estado": n.estado.value,
                "intentos": n.intentos,
                "creado_en": n.creado_en,
                "enviada_en": n.enviada_en,
                "error_mensaje": n.error_mensaje,
                "puede_reenviar": n.puede_reintentar
            }
            for n in notificaciones
        ],
        "estadisticas": {
            "total_enviadas": db.query(Notificacion).filter(Notificacion.estado == "ENVIADA").count(),
            "total_fallidas": db.query(Notificacion).filter(Notificacion.estado == "FALLIDA").count(),
            "total_pendientes": db.query(Notificacion).filter(Notificacion.estado == "PENDIENTE").count()
        }
    }


@router.post("/reenviar/{notificacion_id}")
async def reenviar_notificacion(
    notificacion_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reenvío manual de notificación fallida
    """
    notif = db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    if not notif.puede_reintentar:
        raise HTTPException(
            status_code=400, 
            detail="No se puede reenviar: máximo de intentos alcanzado o estado inválido"
        )

    # Resetear estado
    notif.estado = "PENDIENTE"
    notif.programada_para = datetime.now()

    # Obtener destinatario
    if notif.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
        email_destino = cliente.email
    elif notif.user_id:
        usuario = db.query(User).filter(User.id == notif.user_id).first()
        email_destino = usuario.email
    else:
        email_destino = notif.destinatario_email

    if not email_destino:
        raise HTTPException(status_code=400, detail="No hay email de destino")

    # Reenviar
    background_tasks.add_task(
        email_service.send_email,
        to_email=email_destino,
        subject=notif.asunto,
        body=notif.mensaje,
        notificacion_id=notif.id
    )

    db.commit()

    return {
        "message": "Notificación reenviada",
        "notificacion_id": notificacion_id,
        "destinatario": email_destino
    }
