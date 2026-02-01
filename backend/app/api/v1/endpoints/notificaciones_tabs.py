"""
Endpoints para las pestañas de Notificaciones (previas, día pago, retrasadas, prejudicial).
Datos reales desde BD (cuotas + clientes). Envío de correo al email del cliente (tabla clientes).
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email import send_email
from app.api.v1.endpoints.notificaciones import get_notificaciones_tabs_data

router_previas = APIRouter()
router_dia_pago = APIRouter()
router_retrasadas = APIRouter()
router_prejudicial = APIRouter()


def _enviar_correos_items(items: List[dict], asunto_base: str, cuerpo_base: str) -> dict:
    """Envía un correo por cada item que tenga correo válido. Usa email de tabla clientes (item['correo'])."""
    enviados = 0
    sin_email = 0
    fallidos = 0
    for item in items:
        correo = (item.get("correo") or "").strip()
        if not correo or "@" not in correo:
            sin_email += 1
            continue
        nombre = item.get("nombre") or "Cliente"
        cedula = item.get("cedula") or ""
        fecha_v = item.get("fecha_vencimiento") or ""
        numero_cuota = item.get("numero_cuota")
        monto = item.get("monto_cuota")
        cuerpo = cuerpo_base.format(
            nombre=nombre,
            cedula=cedula,
            fecha_vencimiento=fecha_v,
            numero_cuota=numero_cuota or "",
            monto=monto if monto is not None else "",
        )
        if send_email([correo], asunto_base, cuerpo):
            enviados += 1
        else:
            fallidos += 1
    return {"enviados": enviados, "sin_email": sin_email, "fallidos": fallidos}


# --- Notificaciones previas (5, 3, 1 días antes) ---

@router_previas.get("")
def get_notificaciones_previas(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones previas: cuotas que vencen en 5, 3 o 1 día. Verifica cédula y email en tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["dias_5"] + data["dias_3"] + data["dias_1"]
    return {
        "items": items,
        "total": len(items),
        "dias_5": len(data["dias_5"]),
        "dias_3": len(data["dias_3"]),
        "dias_1": len(data["dias_1"]),
    }


@router_previas.post("/enviar")
def enviar_notificaciones_previas(db: Session = Depends(get_db)):
    """Envía correo a cada cliente en notificaciones previas usando el email de la tabla clientes (por cédula/cliente_id)."""
    data = get_notificaciones_tabs_data(db)
    items = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo)
    return {"mensaje": "Envío de notificaciones previas finalizado.", **res}


# --- Día de pago (vence hoy) ---

@router_dia_pago.get("")
def get_notificaciones_dia_pago(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones del día de pago: cuotas que vencen hoy. Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["hoy"]
    return {"items": items, "total": len(items)}


@router_dia_pago.post("/enviar")
def enviar_notificaciones_dia_pago(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota que vence hoy (email de tabla clientes)."""
    data = get_notificaciones_tabs_data(db)
    items = data["hoy"]
    asunto = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo)
    return {"mensaje": "Envío de notificaciones día de pago finalizado.", **res}


# --- Notificaciones retrasadas (1, 3, 5 días atrasado) ---

@router_retrasadas.get("")
def get_notificaciones_retrasadas(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones retrasadas: cuotas con 1, 3 o 5 días de atraso. Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"]
    return {
        "items": items,
        "total": len(items),
        "dias_1": len(data["dias_1_retraso"]),
        "dias_3": len(data["dias_3_retraso"]),
        "dias_5": len(data["dias_5_retraso"]),
    }


@router_retrasadas.post("/enviar")
def enviar_notificaciones_retrasadas(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota retrasada (email de tabla clientes)."""
    data = get_notificaciones_tabs_data(db)
    items = data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"]
    asunto = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo)
    return {"mensaje": "Envío de notificaciones retrasadas finalizado.", **res}


# --- Notificaciones prejudiciales (3+ cuotas atrasadas) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(estado: str = None, db: Session = Depends(get_db)):
    """Lista de clientes con 3 o más cuotas atrasadas (prejudicial). Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["prejudicial"]
    return {"items": items, "total": len(items)}


@router_prejudicial.post("/enviar")
def enviar_notificaciones_prejudicial(db: Session = Depends(get_db)):
    """Envía correo a cada cliente en situación prejudicial (email de tabla clientes)."""
    data = get_notificaciones_tabs_data(db)
    items = data["prejudicial"]
    asunto = "Aviso prejudicial - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situación.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo)
    return {"mensaje": "Envío de notificaciones prejudiciales finalizado.", **res}
