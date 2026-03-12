"""
Endpoints para las pestañas de Notificaciones (previas, día pago, retrasadas, prejudicial, mora 90+).
Datos reales desde BD (cuotas + clientes). Envío por Email (Configuración > Email) y respeto de
configuración de envíos (habilitado/CCO por tipo) desde BD (notificaciones_envios). get_db en todos los procesos.
"""
from typing import Callable, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email import send_email
from app.core.email_config_holder import sync_from_db as sync_email_config_from_db
from app.core.whatsapp_send import send_whatsapp_text
from app.api.v1.endpoints.notificaciones import (
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
    build_contexto_cobranza_para_item,
)
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes

# Mapeo tipo config (PAGO_5_DIAS_ANTES, etc.) a tipo_tab para estadísticas/rebotados (solo los 5 que muestra la UI)
_CONFIG_TIPO_TO_TAB = {
    "PAGO_5_DIAS_ANTES": "dias_5",
    "PAGO_3_DIAS_ANTES": "dias_3",
    "PAGO_1_DIA_ANTES": "dias_1",
    "PAGO_DIA_0": "hoy",
    "MORA_90": "mora_90",
}


def _tipo_tab_para_persistencia(tipo_config: str) -> str | None:
    """Devuelve tipo_tab (dias_5, hoy, etc.) si se debe persistir para estadísticas/rebotados."""
    return _CONFIG_TIPO_TO_TAB.get(tipo_config)

router_previas = APIRouter(dependencies=[Depends(get_current_user)])
router_dia_pago = APIRouter(dependencies=[Depends(get_current_user)])
router_retrasadas = APIRouter(dependencies=[Depends(get_current_user)])
router_prejudicial = APIRouter(dependencies=[Depends(get_current_user)])
router_mora_90 = APIRouter(dependencies=[Depends(get_current_user)])


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
    - modo_pruebas (desde config): si True y email_pruebas válido, TODOS los emails van SOLO a ese correo (no a clientes).
    - config_envios (desde BD): si tipo tiene habilitado=false no se envía; CCO del tipo se envía como BCC (copia oculta).
    - Si tipo tiene plantilla_id en config, se usa asunto/cuerpo de esa plantilla (con variables sustituidas).
    - Email desde Configuración > Email (holder sincronizado con BD antes de enviar).
    - WhatsApp desde Configuración > WhatsApp (send_whatsapp_text) cuando el item tiene teléfono.
    """
    sync_email_config_from_db()
    modo_pruebas = config_envios.get("modo_pruebas") is True
    email_pruebas = (config_envios.get("email_pruebas") or "").strip()
    usar_solo_pruebas = modo_pruebas and email_pruebas and "@" in email_pruebas
    # Si modo prueba activo pero sin correo válido: no enviar a clientes (evitar envío por error)
    bloqueo_pruebas_sin_email = modo_pruebas and not (email_pruebas and "@" in email_pruebas)

    enviados = 0
    sin_email = 0
    fallidos = 0
    omitidos_config = 0
    enviados_whatsapp = 0
    fallidos_whatsapp = 0
    registros_envio: List[EnvioNotificacion] = []
    correlativos_en_batch = {}
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
        if plantilla_id and db and item.get("prestamo_id") and not item.get("contexto_cobranza"):
            plantilla = db.get(PlantillaNotificacion, plantilla_id)
            if plantilla and getattr(plantilla, "tipo", None) == "COBRANZA":
                ctx, corr = build_contexto_cobranza_para_item(db, item, correlativos_en_batch)
                if ctx is not None:
                    item["contexto_cobranza"] = ctx
                    item["_correlativo_envio"] = corr
        asunto, cuerpo = get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base)
        # Adjunto PDF para plantilla tipo COBRANZA (carta de cobranza)
        attachments = None
        body_html = None
        if plantilla_id and db:
            plantilla = db.get(PlantillaNotificacion, plantilla_id)
            if plantilla and getattr(plantilla, "tipo", None) == "COBRANZA" and item.get("contexto_cobranza"):
                body_html = cuerpo  # el cuerpo de COBRANZA es HTML
                incluir_pdf_anexo = tipo_cfg.get("incluir_pdf_anexo") is not False
                incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos") is not False
                try:
                    attachments = []
                    if incluir_pdf_anexo:
                        pdf_bytes = generar_carta_cobranza_pdf(item["contexto_cobranza"], db=db)
                        attachments.append(("Carta_Cobranza.pdf", pdf_bytes))
                    if incluir_adjuntos_fijos:
                        adjunto_fijo = get_adjunto_fijo_cobranza_bytes(db)
                        if adjunto_fijo:
                            attachments.append(adjunto_fijo)
                    if not attachments:
                        attachments = None
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).exception("Error generando PDF cobranza: %s", e)
        # Email: en modo prueba todos van solo a email_pruebas; en producción al correo del cliente (+ CCO si hay)
        if usar_solo_pruebas:
            to_email = [email_pruebas]
            bcc_list = None
        elif bloqueo_pruebas_sin_email:
            to_email = []  # Modo prueba activo pero sin correo de pruebas: no enviar a nadie
            bcc_list = None
        else:
            correo = (item.get("correo") or "").strip()
            if not correo or "@" not in correo:
                to_email = []
            else:
                to_email = [correo]
            cco = tipo_cfg.get("cco") or []
            bcc_list = [e.strip() for e in cco if e and isinstance(e, str) and "@" in e.strip()] if isinstance(cco, list) else []

        if to_email:
            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
            )
            if ok:
                enviados += 1
            else:
                fallidos += 1
            tipo_tab = _tipo_tab_para_persistencia(tipo)
            if tipo_tab:
                registros_envio.append(
                    EnvioNotificacion(
                        tipo_tab=tipo_tab,
                        email=to_email[0],
                        nombre=(item.get("nombre") or "")[:255],
                        cedula=(item.get("cedula") or "")[:50],
                        exito=ok,
                        error_mensaje=None if ok else (msg or "")[:5000],
                        prestamo_id=item.get("prestamo_id"),
                        correlativo=item.get("_correlativo_envio"),
                    )
                )
        else:
            if not usar_solo_pruebas:
                sin_email += 1
        # WhatsApp (config desde Configuración > WhatsApp; mismo cuerpo que email). En modo prueba no se redirige WhatsApp.
        telefono = (item.get("telefono") or "").strip()
        if telefono:
            ok, _ = send_whatsapp_text(telefono, cuerpo)
            if ok:
                enviados_whatsapp += 1
            else:
                fallidos_whatsapp += 1
    if registros_envio:
        try:
            for r in registros_envio:
                db.add(r)
            db.commit()
        except Exception:
            db.rollback()
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


# --- Mora 90+ días (moroso: cuotas con 90 o más días de atraso) ---

@router_mora_90.get("")
def get_notificaciones_mora_90(estado: str = None, db: Session = Depends(get_db)):
    """Lista de cuotas con 90 o más días de atraso (moroso). Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["mora_90"]
    return {"items": items, "total": len(items)}


def _tipo_mora_90(_item: dict) -> str:
    return "MORA_90"


@router_mora_90.post("/enviar")
def enviar_notificaciones_mora_90(db: Session = Depends(get_db)):
    """Envía correo a cada cliente con cuota 90+ días en mora (moroso). Respeta config envíos (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["mora_90"]
    asunto = "Aviso: cuota en mora 90+ días - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que tiene una cuota con más de 90 días de atraso (estado moroso).\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_mora_90, db)
    return {"mensaje": "Envío de notificaciones mora 90+ finalizado.", **res}


def ejecutar_envio_todas_notificaciones(db: Session) -> dict:
    """
    Ejecuta el envío de todas las notificaciones (previas, día pago, retrasadas, prejudicial, mora 90).
    Pensado para ser llamado por el scheduler (p. ej. diario a las 23:00).
    Respeta configuración de envíos (habilitado/CCO por tipo) desde BD.
    """
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    total_enviados = 0
    total_fallidos = 0
    total_sin_email = 0
    total_omitidos_config = 0
    total_whatsapp_ok = 0
    total_whatsapp_fail = 0
    detalles = {}

    # Previas (5, 3, 1 días antes)
    items_previas = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto_p = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_p = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_previas, asunto_p, cuerpo_p, config_envios, _tipo_previas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["previas"] = r

    # Día de pago (vence hoy)
    items_hoy = data["hoy"]
    asunto_h = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_h = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_hoy, asunto_h, cuerpo_h, config_envios, _tipo_dia_pago, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["dia_pago"] = r

    # Retrasadas (1, 3, 5 días atraso)
    items_retrasadas = data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"]
    asunto_r = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_r = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_retrasadas, asunto_r, cuerpo_r, config_envios, _tipo_retrasadas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["retrasadas"] = r

    # Prejudicial
    items_prejudicial = data["prejudicial"]
    asunto_pre = "Aviso prejudicial - Rapicredit"
    cuerpo_pre = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situación.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_prejudicial, asunto_pre, cuerpo_pre, config_envios, _tipo_prejudicial, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["prejudicial"] = r

    # Mora 90+
    items_mora90 = data["mora_90"]
    asunto_m = "Aviso: cuota en mora 90+ días - Rapicredit"
    cuerpo_m = (
        "Estimado/a {nombre} (cédula {cedula}),\n\n"
        "Le informamos que tiene una cuota con más de 90 días de atraso (estado moroso).\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "Número de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_mora90, asunto_m, cuerpo_m, config_envios, _tipo_mora_90, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["mora_90"] = r

    return {
        "enviados": total_enviados,
        "fallidos": total_fallidos,
        "sin_email": total_sin_email,
        "omitidos_config": total_omitidos_config,
        "enviados_whatsapp": total_whatsapp_ok,
        "fallidos_whatsapp": total_whatsapp_fail,
        "detalles": detalles,
    }
