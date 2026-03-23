"""
Endpoints para notificaciones por cuota (retrasadas 1/3/5 dias, prejudicial).

Politica: sin envios "previos" ni el dia del vencimiento; previas/dia-pago devuelven listas vacias.
Datos reales desde BD. get_db en todos los procesos.

Paquete de correo al cliente (NOTIFICACIONES_PAQUETE_ESTRICTO=True por defecto):
1) Plantilla de correo: HTML/texto con variables sustituidas por datos del cliente/cuota.
2) PDF variable Carta_Cobranza.pdf: generado con variables de cobranza (plantilla PDF / contexto).
3) Al menos un PDF fijo adicional: documentos de pestaña "Documentos PDF anexos" y/o adjunto global;
   siempre se envia junto al PDF variable cuando el paquete es estricto.
"""
import logging
from typing import Callable, List, Optional, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
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
    plantilla_usa_variables_cobranza,
)
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.services.notificaciones_envios_store import coerce_modo_pruebas_notificaciones
from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso
from app.services.notificacion_logging import (
    log_envio_inicio,
    log_envio_config,
    log_envio_contexto_cobranza,
    log_envio_adjuntos,
    log_envio_paquete_incompleto,
    log_envio_email,
    log_envio_persistencia,
    log_envio_resumen,
    log_envio_fallo,
)

# Mapeo tipo config (PAGO_5_DIAS_ANTES, etc.) a tipo_tab para estad�sticas/rebotados (solo los 5 que muestra la UI)
_CONFIG_TIPO_TO_TAB = {
    "PAGO_5_DIAS_ANTES": "dias_5",
    "PAGO_3_DIAS_ANTES": "dias_3",
    "PAGO_1_DIA_ANTES": "dias_1",
    "PAGO_DIA_0": "hoy",
    "PAGO_1_DIA_ATRASADO": "dias_1_retraso",
    "PAGO_3_DIAS_ATRASADO": "dias_3_retraso",
    "PAGO_5_DIAS_ATRASADO": "dias_5_retraso",
    "PREJUDICIAL": "prejudicial",
}


def _tipo_tab_para_persistencia(tipo_config: str) -> str | None:
    """Devuelve tipo_tab (dias_5, hoy, etc.) si se debe persistir para estad�sticas/rebotados."""
    return _CONFIG_TIPO_TO_TAB.get(tipo_config)


NOMBRE_PDF_CARTA_VARIABLE = "Carta_Cobranza.pdf"


def _cfg_incluir_pdf_anexo(tipo_cfg: dict) -> bool:
    """
    Pestaña 2 (PDF carta): activo por defecto, igual que ConfiguracionNotificaciones.tsx
    (incluir_pdf_anexo !== false). Si la clave falta en JSON antiguo, antes el backend usaba
    False y no adjuntaba ni en modo estricto bloqueaba el envío.
    """
    if not isinstance(tipo_cfg, dict):
        return True
    if "incluir_pdf_anexo" not in tipo_cfg:
        return True
    v = tipo_cfg["incluir_pdf_anexo"]
    if v is None or v is True:
        return True
    if v is False:
        return False
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("0", "false", "no", "off", ""):
            return False
        if s in ("1", "true", "yes", "si", "sí"):
            return True
        return bool(s)
    return bool(v)


def _parse_plantilla_id_desde_config(raw) -> Optional[int]:
    """Acepta int, str '42', float desde JSON; None si inválido."""
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None


def _bytes_son_pdf_valido(data: Optional[bytes]) -> bool:
    if not data or len(data) < 4:
        return False
    return data[:4] == b"%PDF"


def _validar_plantilla_email_estricta(db, plantilla_id: Optional[int]) -> tuple[bool, str]:
    """Exige plantilla en BD, activa, con asunto y cuerpo no vacios."""
    if not plantilla_id:
        return False, "sin_plantilla_id"
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p or not p.activa:
        return False, "plantilla_inactiva_o_ausente"
    if not (p.asunto or "").strip() or not (p.cuerpo or "").strip():
        return False, "plantilla_asunto_o_cuerpo_vacio"
    return True, ""


def _adjuntos_cumplen_paquete_completo(
    attachments: Optional[List[Tuple[str, bytes]]],
) -> tuple[bool, str]:
    """
    Debe existir el PDF variable (Carta_Cobranza.pdf) valido y al menos un PDF fijo adicional valido.
    Los fijos son cualquier adjunto distinto del nombre de la carta.
    """
    if not attachments:
        return False, "sin_adjuntos"
    carta: Optional[bytes] = None
    otros: List[bytes] = []
    for nombre, data in attachments:
        if nombre == NOMBRE_PDF_CARTA_VARIABLE:
            carta = data
        else:
            otros.append(data)
    if not _bytes_son_pdf_valido(carta):
        return False, "falta_pdf_variable_o_invalido"
    if not any(_bytes_son_pdf_valido(d) for d in otros):
        if len(otros) == 0:
            return (
                False,
                "falta_pdf_fijo_solo_Carta_Cobranza: anexar PDF pestaña 3 (caso dias_1_retraso) y/o "
                "adjunto global configuracion adjunto_fijo_cobranza; en Render el archivo debe existir en disco persistente",
            )
        return (
            False,
            "falta_pdf_fijo_no_cabecera_PDF: hay archivo extra pero no empieza con %PDF (no es PDF valido o corrupto)",
        )
    return True, ""


router_previas = APIRouter(dependencies=[Depends(get_current_user)])
router_dia_pago = APIRouter(dependencies=[Depends(get_current_user)])
router_retrasadas = APIRouter(dependencies=[Depends(get_current_user)])
router_prejudicial = APIRouter(dependencies=[Depends(get_current_user)])


def _enviar_correos_items(
    items: List[dict],
    asunto_base: str,
    cuerpo_base: str,
    config_envios: dict,
    get_tipo_for_item: Callable[[dict], str],
    db,
) -> dict:
    """
    Envia por Email y/o WhatsApp por cada item.

    Modo pruebas: todos los envíos van al email de pruebas; plantillas y PDF usan datos reales.
    Modo producción: envío al correo de cada cliente; plantillas y PDF con datos reales.

    Con NOTIFICACIONES_PAQUETE_ESTRICTO=True (defecto): no se envia correo ni WhatsApp sin
    plantilla email activa, PDF Carta_Cobranza valido y al menos un PDF fijo adicional.
    Desactivar solo en emergencia vía .env (NOTIFICACIONES_PAQUETE_ESTRICTO=false).
    """
    sync_email_config_from_db()
    modo_pruebas = coerce_modo_pruebas_notificaciones(config_envios.get("modo_pruebas"))
    paquete_estricto = bool(getattr(settings, "NOTIFICACIONES_PAQUETE_ESTRICTO", True))
    log_envio_inicio(len(items), "batch", modo_pruebas=modo_pruebas)
    email_pruebas = (config_envios.get("email_pruebas") or "").strip()
    usar_solo_pruebas = modo_pruebas and email_pruebas and "@" in email_pruebas
    # Si modo prueba activo pero sin correo v�lido: no enviar a clientes (evitar env�o por error)
    bloqueo_pruebas_sin_email = modo_pruebas and not (email_pruebas and "@" in email_pruebas)
    # Incluir caso cuando Envío está activo; solo excluir si habilitado está explícitamente en False
    habilitados = sum(1 for v in config_envios.values() if isinstance(v, dict) and v.get("habilitado", True) is not False)
    log_envio_config(modo_pruebas, bool(email_pruebas and "@" in email_pruebas), habilitados)
    if habilitados == 0:
        logger = logging.getLogger(__name__)
        logger.warning(
            "[notif_envio_config] Ningún tipo de notificación está habilitado. "
            "Habilite al menos uno en Configuración > Notificaciones > Envíos (por caso: Faltan 5 días, Hoy vence, etc.) "
            "para que se envíen correos; si no, todos los ítems se omiten (omitidos_config)."
        )

    enviados = 0
    sin_email = 0
    fallidos = 0
    omitidos_config = 0
    omitidos_paquete_incompleto = 0
    enviados_whatsapp = 0
    fallidos_whatsapp = 0
    registros_envio: List[EnvioNotificacion] = []
    correlativos_en_batch = {}
    for idx, item in enumerate(items):
        item_id_log = item.get("cedula") or str(item.get("prestamo_id") or idx)
        tipo = get_tipo_for_item(item)
        tipo_cfg = config_envios.get(tipo) or {}
        # Omitir solo cuando "Envío" está explícitamente desactivado (habilitado=False)
        if tipo_cfg.get("habilitado", True) is False:
            omitidos_config += 1
            continue
        plantilla_id = _parse_plantilla_id_desde_config(tipo_cfg.get("plantilla_id"))

        if paquete_estricto and db:
            ok_plant, mot_plant = _validar_plantilla_email_estricta(db, plantilla_id)
            if not ok_plant:
                log_envio_paquete_incompleto(item_id_log, mot_plant, tipo)
                omitidos_paquete_incompleto += 1
                continue
            if not _cfg_incluir_pdf_anexo(tipo_cfg):
                log_envio_paquete_incompleto(
                    item_id_log, "incluir_pdf_anexo_desactivado_en_config", tipo
                )
                omitidos_paquete_incompleto += 1
                continue
            if tipo_cfg.get("incluir_adjuntos_fijos", True) is False:
                log_envio_paquete_incompleto(
                    item_id_log, "incluir_adjuntos_fijos_no_puede_desactivarse", tipo
                )
                omitidos_paquete_incompleto += 1
                continue
            if not item.get("prestamo_id"):
                log_envio_paquete_incompleto(
                    item_id_log, "sin_prestamo_id_para_pdf_carta", tipo
                )
                omitidos_paquete_incompleto += 1
                continue

        # Construir contexto_cobranza cuando haga falta: email COBRANZA, adjunto PDF (Carta_Cobranza) o plantilla con variables cobranza
        # Si "Incluir PDF" está marcado pero no hay plantilla (Texto por defecto), igual se construye contexto para adjuntar Carta_Cobranza.pdf
        if db and item.get("prestamo_id") and not item.get("contexto_cobranza"):
            plantilla = db.get(PlantillaNotificacion, plantilla_id) if plantilla_id else None
            need_ctx = paquete_estricto or (
                (plantilla and getattr(plantilla, "tipo", None) == "COBRANZA")
                or _cfg_incluir_pdf_anexo(tipo_cfg)
                or (plantilla and plantilla_usa_variables_cobranza(plantilla))
            )
            if need_ctx:
                ctx, corr = build_contexto_cobranza_para_item(db, item, correlativos_en_batch)
                if ctx is not None:
                    item["contexto_cobranza"] = ctx
                    item["_correlativo_envio"] = corr
                    log_envio_contexto_cobranza(item_id_log, True)
                else:
                    log_envio_contexto_cobranza(item_id_log, False, motivo="build_contexto_cobranza devolvió None")
        # Siempre datos reales en plantillas; en modo pruebas solo cambia el destinatario (email_pruebas)
        asunto, cuerpo = get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base, modo_pruebas=False)
        # Adjuntos disponibles en todas las pestañas según config: PDF con variables (carta cobranza) y PDF(s) fijos
        attachments: Optional[List[Tuple[str, bytes]]] = None
        body_html = None
        if plantilla_id and db:
            plantilla = db.get(PlantillaNotificacion, plantilla_id)
            if plantilla and item.get("contexto_cobranza") and (
                getattr(plantilla, "tipo", None) == "COBRANZA" or plantilla_usa_variables_cobranza(plantilla)
            ):
                body_html = cuerpo  # cuerpo renderizado con variables cobranza es HTML
        # Si el cuerpo parece HTML (cualquier plantilla con tabla/div/p/html), enviar como HTML para que el cliente lo renderice
        if body_html is None and cuerpo and "<" in cuerpo and ">" in cuerpo:
            _c = cuerpo.lower()
            if any(tag in _c for tag in ("<table", "</table>", "<div", "<p ", "<span", "<html", "<body", "<br", "<h1", "<h2", "<h3")):
                body_html = cuerpo
        # Adjuntos obligatorios cuando están seleccionados en Config (Notificaciones → Envíos):
        # - PDF (pestaña 2): Carta_Cobranza.pdf generada desde Plantilla anexo PDF. Se agrega OBLIGATORIAMENTE si incluir_pdf_anexo=True.
        # - Adj. (pestaña 3): Documentos PDF fijos subidos en Documentos PDF anexos. Se agregan OBLIGATORIAMENTE si incluir_adjuntos_fijos no es False.
        if paquete_estricto:
            incluir_pdf_anexo = True
            incluir_adjuntos_fijos = True
        else:
            incluir_pdf_anexo = _cfg_incluir_pdf_anexo(tipo_cfg)
            incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos", True) is not False  # True si falta la clave (compatibilidad)
        if incluir_pdf_anexo or incluir_adjuntos_fijos:
            try:
                attachments = []
                if incluir_pdf_anexo:
                    ctx_pdf = item.get("contexto_cobranza")
                    if ctx_pdf:
                        pdf_bytes = generar_carta_cobranza_pdf(ctx_pdf, db=db)
                        attachments.append((NOMBRE_PDF_CARTA_VARIABLE, pdf_bytes))
                if incluir_adjuntos_fijos and db:
                    adjunto_fijo = get_adjunto_fijo_cobranza_bytes(db)
                    if adjunto_fijo:
                        attachments.append(adjunto_fijo)
                    tipo_caso = _CONFIG_TIPO_TO_TAB.get(tipo)
                    if tipo_caso:
                        for nombre, contenido in get_adjuntos_fijos_por_caso(db, tipo_caso):
                            attachments.append((nombre, contenido))
                if not attachments:
                    attachments = None
                _nombres_adj = (
                    ",".join(str(a[0]) for a in attachments if a and len(a) > 0)[:400]
                    if attachments
                    else ""
                )
                log_envio_adjuntos(
                    item_id_log,
                    len(attachments) if attachments else 0,
                    nombres=_nombres_adj or None,
                )
            except Exception as e:
                log_envio_adjuntos(
                    item_id_log,
                    len(attachments) if attachments else 0,
                    error=str(e),
                )
                log_envio_fallo("adjuntos", str(e), exc=e)
                if not attachments:
                    attachments = None
        if paquete_estricto:
            ok_pkg, mot_pkg = _adjuntos_cumplen_paquete_completo(attachments)
            if not ok_pkg:
                log_envio_paquete_incompleto(item_id_log, mot_pkg, tipo)
                omitidos_paquete_incompleto += 1
                continue

        # Los adjuntos construidos se pasan SIEMPRE a send_email (attachments=None o lista no vacía).
        # Destinatario: en modo prueba todos van solo a email_pruebas; en producci�n al correo del cliente (+ CCO si hay)
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

        email_sent_ok = False
        if to_email:
            tipo_tab_envio = _tipo_tab_para_persistencia(tipo)
            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
                tipo_tab=tipo_tab_envio,
            )
            log_envio_email(item_id_log, to_email[0], ok, None if ok else msg)
            email_sent_ok = ok
            if ok:
                enviados += 1
            else:
                fallidos += 1
            tipo_tab = _tipo_tab_para_persistencia(tipo)
            if tipo_tab:
                registros_envio.append(
                    EnvioNotificacion(
                        tipo_tab=tipo_tab,
                        asunto=(asunto or "")[:500] if asunto else None,
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
        # WhatsApp solo si el correo se envio OK (paquete ya validado arriba).
        telefono = (item.get("telefono") or "").strip()
        if telefono and email_sent_ok:
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
            log_envio_persistencia(len(registros_envio), True)
        except Exception as e:
            db.rollback()
            log_envio_persistencia(len(registros_envio), False, error=str(e))
            log_envio_fallo("persistencia", str(e), exc=e)
    log_envio_resumen(
        enviados=enviados,
        fallidos=fallidos,
        sin_email=sin_email,
        omitidos_config=omitidos_config,
        enviados_whatsapp=enviados_whatsapp,
        fallidos_whatsapp=fallidos_whatsapp,
        modo_pruebas=modo_pruebas,
        omitidos_paquete_incompleto=omitidos_paquete_incompleto,
    )
    if enviados == 0 and len(items) > 0:
        log = logging.getLogger(__name__)
        if omitidos_paquete_incompleto > 0 and paquete_estricto:
            log.warning(
                "[notif_envio_diagnostico] enviados=0: %s items omitidos por paquete incompleto "
                "(NOTIFICACIONES_PAQUETE_ESTRICTO=true). Se exige Carta_Cobranza.pdf + al menos un PDF fijo "
                "valido (%%PDF). Configure adjuntos en pestaña 3 por caso y/o adjunto global; en Render use disco "
                "persistente. Emergencia: NOTIFICACIONES_PAQUETE_ESTRICTO=false en .env.",
                omitidos_paquete_incompleto,
            )
        if omitidos_config > 0 and omitidos_paquete_incompleto == 0 and habilitados == 0:
            log.warning(
                "[notif_envio_diagnostico] enviados=0: ningun tipo tiene envio habilitado en "
                "Configuracion > Notificaciones > Envios (habilitado=false en todos).",
            )
        if bloqueo_pruebas_sin_email:
            log.warning(
                "[notif_envio_diagnostico] enviados=0: modo pruebas activo pero falta email_pruebas valido en "
                "notificaciones_envios; no se envia a clientes.",
            )
        if fallidos > 0:
            log.warning(
                "[notif_envio_diagnostico] enviados=0 pero fallidos=%s: revisar logs [SMTP_ENVIO] (SMTP, contrasena, rechazo).",
                fallidos,
            )
        if sin_email > 0 and not modo_pruebas and omitidos_paquete_incompleto == 0:
            log.warning(
                "[notif_envio_diagnostico] %s items sin correo de cliente en datos; no hay destinatario.",
                sin_email,
            )
    return {
        "enviados": enviados,
        "sin_email": sin_email,
        "fallidos": fallidos,
        "omitidos_config": omitidos_config,
        "omitidos_paquete_incompleto": omitidos_paquete_incompleto,
        "enviados_whatsapp": enviados_whatsapp,
        "fallidos_whatsapp": fallidos_whatsapp,
    }


# --- Notificaciones previas (5, 3, 1 d�as antes) ---

@router_previas.get("")
def get_notificaciones_previas(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones previas: cuotas que vencen en 5, 3 o 1 d�a. Verifica c�dula y email en tabla clientes."""
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
    """Env�a correo a cada cliente en notificaciones previas. Respeta config env�os (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_previas, db)
    return {"mensaje": "Env�o de notificaciones previas finalizado.", **res}


# --- D�a de pago (vence hoy) ---

@router_dia_pago.get("")
def get_notificaciones_dia_pago(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones del d�a de pago: cuotas que vencen hoy. Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["hoy"]
    return {"items": items, "total": len(items)}


def _tipo_dia_pago(_item: dict) -> str:
    return "PAGO_DIA_0"


@router_dia_pago.post("/enviar")
def enviar_notificaciones_dia_pago(db: Session = Depends(get_db)):
    """Env�a correo a cada cliente con cuota que vence hoy. Respeta config env�os (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["hoy"]
    asunto = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_dia_pago, db)
    return {"mensaje": "Env�o de notificaciones d�a de pago finalizado.", **res}


# --- Notificaciones retrasadas (1, 3, 5 d�as atrasado) ---

@router_retrasadas.get("")
def get_notificaciones_retrasadas(estado: str = None, db: Session = Depends(get_db)):
    """Lista de notificaciones retrasadas: cuotas con 1, 3 o 5 d�as de atraso. Email desde tabla clientes."""
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
    """Env�a correo a cada cliente con cuota retrasada. Respeta config env�os (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"]
    asunto = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_retrasadas, db)
    return {"mensaje": "Env�o de notificaciones retrasadas finalizado.", **res}


# --- Notificaciones prejudiciales (3+ cuotas atrasadas) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(estado: str = None, db: Session = Depends(get_db)):
    """Lista de clientes con 3 o m�s cuotas atrasadas (prejudicial). Email desde tabla clientes."""
    data = get_notificaciones_tabs_data(db)
    items = data["prejudicial"]
    return {"items": items, "total": len(items)}


def _tipo_prejudicial(_item: dict) -> str:
    return "PREJUDICIAL"


@router_prejudicial.post("/enviar")
def enviar_notificaciones_prejudicial(db: Session = Depends(get_db)):
    """Env�a correo a cada cliente en situaci�n prejudicial. Respeta config env�os (habilitado/CCO) desde BD."""
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    items = data["prejudicial"]
    asunto = "Aviso prejudicial - Rapicredit"
    cuerpo = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci�n.\n\n"
        "Saludos,\nRapicredit"
    )
    res = _enviar_correos_items(items, asunto, cuerpo, config_envios, _tipo_prejudicial, db)
    return {"mensaje": "Env�o de notificaciones prejudiciales finalizado.", **res}


def ejecutar_envio_todas_notificaciones(db: Session) -> dict:
    """
    Ejecuta el env�o de todas las notificaciones (previas, d�a pago, retrasadas, prejudicial).
    Pensado para ser llamado por el scheduler (p. ej. diario a la 01:00 America/Caracas).
    Respeta configuraci�n de env�os (habilitado/CCO por tipo) desde BD.
    """
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db)
    total_enviados = 0
    total_fallidos = 0
    total_sin_email = 0
    total_omitidos_config = 0
    total_omitidos_paquete = 0
    total_whatsapp_ok = 0
    total_whatsapp_fail = 0
    detalles = {}

    # Previas (5, 3, 1 d�as antes)
    items_previas = data["dias_5"] + data["dias_3"] + data["dias_1"]
    asunto_p = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_p = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_previas, asunto_p, cuerpo_p, config_envios, _tipo_previas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["previas"] = r

    # D�a de pago (vence hoy)
    items_hoy = data["hoy"]
    asunto_h = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_h = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_hoy, asunto_h, cuerpo_h, config_envios, _tipo_dia_pago, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["dia_pago"] = r

    # Retrasadas (1, 3, 5 d�as atraso)
    items_retrasadas = data["dias_1_retraso"] + data["dias_3_retraso"] + data["dias_5_retraso"]
    asunto_r = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_r = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N�mero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_retrasadas, asunto_r, cuerpo_r, config_envios, _tipo_retrasadas, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["retrasadas"] = r

    # Prejudicial
    items_prejudicial = data["prejudicial"]
    asunto_pre = "Aviso prejudicial - Rapicredit"
    cuerpo_pre = (
        "Estimado/a {nombre} (c�dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci�n.\n\n"
        "Saludos,\nRapicredit"
    )
    r = _enviar_correos_items(items_prejudicial, asunto_pre, cuerpo_pre, config_envios, _tipo_prejudicial, db)
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["prejudicial"] = r

    return {
        "enviados": total_enviados,
        "fallidos": total_fallidos,
        "sin_email": total_sin_email,
        "omitidos_config": total_omitidos_config,
        "omitidos_paquete_incompleto": total_omitidos_paquete,
        "enviados_whatsapp": total_whatsapp_ok,
        "fallidos_whatsapp": total_whatsapp_fail,
        "detalles": detalles,
    }
