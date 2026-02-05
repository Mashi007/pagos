"""
Endpoints para las pestañas de Notificaciones (previas, día pago, retrasadas, prejudicial, mora 61).
Datos reales desde BD (cuotas + clientes). Envío por Email (Configuración > Email) y respeto de
configuración de envíos (habilitado/CCO por tipo) desde BD (notificaciones_envios). get_db en todos los procesos.
"""
from typing import Callable, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email import send_email
from app.core.whatsapp_send import send_whatsapp_text
from app.api.v1.endpoints.notificaciones import (
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
)

router_previas = APIRouter(dependencies=[Depends(get_current_user)])
router_dia_pago = APIRouter(dependencies=[Depends(get_current_user)])
router_retrasadas = APIRouter(dependencies=[Depends(get_current_user)])
router_prejudicial = APIRouter(dependencies=[Depends(get_current_user)])
router_mora_61 = APIRouter(dependencies=[Depends(get_current_user)])


def _enviar_correos_items(
    items: List[dict],
    asunto_base: str,
    cuerpo_base: str,
    config_envios: dict,
    get_tipo_for_item: Callable[[dict], str],
    db,
) -> dict:
    """
    Envía por Email y/o WhatsApp por cada item. Respeta reglas de negocio:
    - config_envios (desde BD): si tipo tiene habilitado=false no se envía; CCO del tipo se añade al correo.
    - Si tipo tiene plantilla_id en config, se usa asunto/cuerpo de esa plantilla (con variables sustituidas).
    - Email desde Configuración > Email (sync_from_db en send_email).
    - WhatsApp desde Configuración > WhatsApp (send_whatsapp_text) cuando el item tiene teléfono.
    """
    enviados = 0
    sin_email = 0
    fallidos = 0
    omitidos_config = 0
    enviados_whatsapp = 0
    fallidos_whatsapp = 0
    for item in items:
        tipo = get_tipo_for_item(item)
        tipo_cfg = config_envios.get(tipo) or {}
        if tipo_cfg.get("habilitado") is False:
            omitidos_config += 1
            continue
        raw_id = tipo_cfg.get("plantilla_id")
        try:
            plantilla_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            plantilla_id = None
        asunto, cuerpo = get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base)
        # Email (config desde Configuración > Email)
        correo = (item.get("correo") or "").strip()
        if correo and "@" in correo:
            cco = tipo_cfg.get("cco") or []
            cc_list = [e.strip() for e in cco if e and isinstance(e, str) and "@" in e.strip()] if isinstance(cco, list) else []
            ok, _ = send_email([correo], asunto_base, cuerpo, cc_emails=cc_list or None)
            if ok:
                enviados += 1
            else:
                fallidos += 1
        else:
            sin_email += 1
        # WhatsApp (config desde Configuración > WhatsApp; mismo cuerpo que email)
        telefono = (item.get("telefono") or "").strip()
        if telefono:
            ok, _ = send_whatsapp_text(telefono, cuerpo)
            if ok:
                enviados_whatsapp += 1
            else:
                fallidos_whatsapp += 1
    return {
        "enviados": enviados,
        "sin_email": sin_email,
        "fallidos": fallidos,
        "omitidos_config": omitidos_config,
        "enviados_whatsapp": enviados_whatsapp,
        "fallidos_whatsapp": fallidos_whatsapp,
    }


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


def _tipo_previas(item: dict) -> str:
    d = item.get("dias_antes_vencimiento")
    return {5: "PAGO_5_DIAS_ANTES", 3: "PAGO_3_DIAS_ANTES", 1: "PAGO_1_DIA_ANTES"}.get(d, "PAGO_5_DIAS_ANTES")


@router_previas.post("/enviar")
def enviar_notificaciones_previas(db: Session = Depends(get_db)):
    """Envía correo a cada cliente en notificaciones previas. Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
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
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_previas, db)
    return {"mensaje": "Envío de notificaciones previas finalizado.", **res}


# --- Día de pago (vence hoy) ---

@router_dia_pago.get("")
def get_notificaciones_dia_pago(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones del día de pago: cuotas que vencen hoy. Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["hoy"]
    return {"items": items, "total": len(items)}


def _tipo_dia_pago(_item: dict) -> str:
    return "PAGO_DIA_0"


@router_dia_pago.post("/enviar")
def enviar_notificaciones_dia_pago(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota que vence hoy. Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
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
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_dia_pago, db)
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


def _tipo_retrasadas(item: dict) -> str:
    d = item.get("dias_atraso")
    return {1: "PAGO_1_DIA_ATRASADO", 3: "PAGO_3_DIAS_ATRASADO", 5: "PAGO_5_DIAS_ATRASADO"}.get(d, "PAGO_1_DIA_ATRASADO")


@router_retrasadas.post("/enviar")
def enviar_notificaciones_retrasadas(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota retrasada. Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
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
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_retrasadas, db)
    return {"mensaje": "Envío de notificaciones retrasadas finalizado.", **res}


# --- Notificaciones prejudiciales (3+ cuotas atrasadas) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(estado: str = None, db: Session = Depends(get_db)):
    """Lista de clientes con 3 o más cuotas atrasadas (prejudicial). Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["prejudicial"]
    return {"items": items, "total": len(items)}


def _tipo_prejudicial(_item: dict) -> str:
    return "PREJUDICIAL"


@router_prejudicial.post("/enviar")
def enviar_notificaciones_prejudicial(db: Session = Depends(get_db)):
    """Envía correo a cada cliente en situación prejudicial. Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
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
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_prejudicial, db)
    return {"mensaje": "Envío de notificaciones prejudiciales finalizado.", **res}


# --- Mora 61+ días (cuotas con 61 o más días de atraso) ---

@router_mora_61.get("")
def get_notificaciones_mora_61(estado: str = None, db: Session = Depends(get_db)):
    """Lista de cuotas con 61 o más días de atraso. Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["mora_61"]
    return {"items": items, "total": len(items)}


def _tipo_mora_61(_item: dict) -> str:
    return "MORA_61"


@router_mora_61.post("/enviar")
def enviar_notificaciones_mora_61(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota 61+ días en mora. Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["mora_61"]
    asunto = "Aviso: cuota en mora 61+ días - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que tiene una cuota con más de 61 días de atraso.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_mora_61, db)
    return {"mensaje": "Envío de notificaciones mora 61+ finalizado.", **res}
