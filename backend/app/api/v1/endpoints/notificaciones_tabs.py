"""
Endpoints para notificaciones por cuota (retrasadas 1/3/5 dias, prejudicial).
Routers: solo rol admin (Depends(require_admin)).

Politica: sin envios "previos" ni el dia del vencimiento; previas/dia-pago devuelven listas vacias.
Datos reales desde BD. get_db en todos los procesos.

Paquete de correo al cliente (NOTIFICACIONES_PAQUETE_ESTRICTO=True por defecto):
1) Plantilla de correo: HTML/texto con variables sustituidas por datos del cliente/cuota.
2) PDF variable Carta_Cobranza.pdf: generado con variables de cobranza (plantilla PDF / contexto).
3) Al menos un PDF fijo adicional: documentos de pestaña "Documentos PDF anexos" y/o adjunto global;
   siempre se envia junto al PDF variable cuando el paquete es estricto.

Excepcion PAGO_2_DIAS_ANTES_PENDIENTE («2 dias antes»): no se exige plantilla guardada en BD
(textos por defecto del modulo si falta plantilla_id) ni Carta_Cobranza / adjuntos obligatorios;
los PDFs de pestañas 2 y 3 son opcionales segun la fila de configuracion.
"""
import logging
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.email import cuerpo_parece_html, send_email
from app.core.email_config_holder import sync_from_db as sync_email_config_from_db
from app.core.whatsapp_send import send_whatsapp_text
from app.api.v1.endpoints.notificaciones import (
    build_prejudicial_items,
    get_notificaciones_tabs_data,
    get_notificaciones_envios_config,
    get_plantilla_asunto_cuerpo,
    build_contexto_cobranza_para_item,
    contexto_cobranza_aplica_a_prestamo,
    plantilla_usa_variables_cobranza,
)
from app.models.cliente import Cliente
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.services.envio_notificacion_snapshot import persistir_snapshot_envio_notificacion
from app.services.notificaciones_envios_store import coerce_modo_pruebas_notificaciones
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_tiene_prestamo_desistimiento,
)
from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso
from app.services.notificacion_service import build_cuotas_pendiente_2_dias_antes_items
from app.utils.cliente_emails import (
    lista_correo_principal_para_notificaciones,
    lista_correo_principal_notificaciones_desde_objeto,
    unir_destinatarios_log,
)
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
    "PAGO_2_DIAS_ANTES_PENDIENTE": "d_2_antes_vencimiento",
    "PAGO_DIA_0": "hoy",
    "PAGO_1_DIA_ATRASADO": "dias_1_retraso",
    "PAGO_3_DIAS_ATRASADO": "dias_3_retraso",
    "PAGO_5_DIAS_ATRASADO": "dias_5_retraso",
    "PAGO_30_DIAS_ATRASADO": "dias_30_retraso",
    "PREJUDICIAL": "prejudicial",
    "MASIVOS": "masivos",
}

# Textos por defecto si no hay plantilla en BD (PAGO_2_DIAS_ANTES_PENDIENTE / 2 dias antes).
# Variables: {nombre}, {fecha_vencimiento_display} (tambien {{nombre}}, {{fecha_vencimiento_display}} en plantillas guardadas).
ASUNTO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE = (
    "Recordatorio: pr\u00f3ximo vencimiento de tu cuota - Rapicredit"
)
CUERPO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE = (
    "Hola, {nombre}.\n\n"
    "Esperamos que est\u00e9s muy bien. Te escribimos para recordarte que el pago de tu pr\u00f3xima cuota "
    "vence el {fecha_vencimiento_display}.\n\n"
    "Mantener tus pagos al d\u00eda te permite seguir disfrutando de nuestros beneficios. Si deseas "
    "verificar el monto exacto a pagar, puedes revisarlo en el siguiente enlace:\n\n"
    "\U0001f449 Consulta tu Estado de Cuenta aqu\u00ed: https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta\n\n"
    "\u00bfTienes alguna duda?\n"
    "Si necesitas ayuda o quieres aclarar algo, estamos a tu disposici\u00f3n por WhatsApp:\n\n"
    "N\u00famero: +58 424-4579934\n\n"
    "Chat directo: https://wa.me/584244579934\n\n"
    "Nota sobre la actualizaci\u00f3n de tu pago:\n"
    "Recuerde que el tiempo de actualizaci\u00f3n de su estado de cuenta depende de:\n\n"
    "\U0001f680 Portal de pagos (sistema autom\u00e1tico):\n"
    "Su pago se reflejar\u00e1 en 24 horas.\n"
    "Reporte aqu\u00ed: https://rapicredit.onrender.com/pagos/rapicredit-cobros\n"
)


def _tipo_tab_para_persistencia(tipo_config: str) -> str | None:
    """Devuelve tipo_tab (dias_5, hoy, etc.) si se debe persistir para estad�sticas/rebotados."""
    return _CONFIG_TIPO_TO_TAB.get(tipo_config)


NOMBRE_PDF_CARTA_VARIABLE = "Carta_Cobranza.pdf"


def _tipo_dos_dias_antes_solo_correo(tipo: str) -> bool:
    """True para «2 dias antes»: envio de correo sin paquete cobranza obligatorio (plantilla opcional en BD)."""
    return tipo == "PAGO_2_DIAS_ANTES_PENDIENTE"


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
    Debe existir el PDF variable (Carta_Cobranza.pdf) valido.
    Ya no se exige un PDF fijo adicional para permitir operación estable en entornos
    con disco efímero (p. ej. Render sin volumen persistente).
    """
    if not attachments:
        return False, "sin_adjuntos"
    carta: Optional[bytes] = None
    for nombre, data in attachments:
        if nombre == NOMBRE_PDF_CARTA_VARIABLE:
            carta = data
    if not _bytes_son_pdf_valido(carta):
        return False, "falta_pdf_variable_o_invalido"
    return True, ""


router_previas = APIRouter(dependencies=[Depends(require_admin)])
router_dia_pago = APIRouter(dependencies=[Depends(require_admin)])
router_retrasadas = APIRouter(dependencies=[Depends(require_admin)])
router_prejudicial = APIRouter(dependencies=[Depends(require_admin)])
router_masivos = APIRouter(dependencies=[Depends(require_admin)])


def _fecha_referencia_desde_query(fecha_caracas: Optional[str]) -> Optional[date]:
    from app.services.cuota_estado import parse_fecha_referencia_negocio

    try:
        return parse_fecha_referencia_negocio(fecha_caracas)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _enviar_correos_items(
    items: List[dict],
    asunto_base: str,
    cuerpo_base: str,
    config_envios: dict,
    get_tipo_for_item: Callable[[dict], str],
    db,
    forzar_destinos_prueba: Optional[List[str]] = None,
    fecha_referencia: Optional[date] = None,
) -> dict:
    """
    Envia por Email y/o WhatsApp por cada item.

    Modo pruebas: todos los envíos van al email de pruebas; plantillas y PDF usan datos reales.
    Modo producción: envío al correo de cada cliente; plantillas y PDF con datos reales.

    Con NOTIFICACIONES_PAQUETE_ESTRICTO=True (defecto): no se envia correo ni WhatsApp sin
    plantilla email activa y PDF Carta_Cobranza valido (salvo PAGO_2_DIAS_ANTES_PENDIENTE: solo correo).
    Desactivar solo en emergencia vía .env (NOTIFICACIONES_PAQUETE_ESTRICTO=false).
    """
    if forzar_destinos_prueba is not None:
        if len(items) != 1:
            raise ValueError("forzar_destinos_prueba requiere exactamente un item")
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
    omitidos_desistimiento = 0
    registros_envio: List[Tuple[EnvioNotificacion, Optional[List[Tuple[str, bytes]]]]] = []
    correlativos_en_batch = {}
    for idx, item in enumerate(items):
        item_id_log = item.get("cedula") or str(item.get("prestamo_id") or idx)
        tipo = get_tipo_for_item(item)
        cid = item.get("cliente_id")
        if db and cliente_tiene_prestamo_desistimiento(db, cid):
            logger.info(
                "[notif_excl_desist] Omitido cliente_id=%s item=%s tipo=%s (prestamo DESISTIMIENTO)",
                cid,
                item_id_log,
                tipo,
            )
            omitidos_desistimiento += 1
            continue
        tipo_cfg = config_envios.get(tipo) or {}
        # Masivos: nunca carta PDF de cobranza ni contexto de préstamo (comunicación general).
        if tipo == "MASIVOS":
            item.pop("contexto_cobranza", None)
            item.pop("_correlativo_envio", None)
            item.pop("prestamo_id", None)
        # Omitir solo cuando "Envío" está explícitamente desactivado (habilitado=False)
        if tipo_cfg.get("habilitado", True) is False:
            omitidos_config += 1
            continue
        plantilla_id = _parse_plantilla_id_desde_config(tipo_cfg.get("plantilla_id"))

        if paquete_estricto and db:
            if not _tipo_dos_dias_antes_solo_correo(tipo):
                ok_plant, mot_plant = _validar_plantilla_email_estricta(db, plantilla_id)
                if not ok_plant:
                    log_envio_paquete_incompleto(item_id_log, mot_plant, tipo)
                    omitidos_paquete_incompleto += 1
                    continue
            requiere_pdf_cobranza = tipo != "MASIVOS" and not _tipo_dos_dias_antes_solo_correo(tipo)
            if requiere_pdf_cobranza and not _cfg_incluir_pdf_anexo(tipo_cfg):
                log_envio_paquete_incompleto(
                    item_id_log, "incluir_pdf_anexo_desactivado_en_config", tipo
                )
                omitidos_paquete_incompleto += 1
                continue
            if requiere_pdf_cobranza and tipo_cfg.get("incluir_adjuntos_fijos", True) is False:
                log_envio_paquete_incompleto(
                    item_id_log, "incluir_adjuntos_fijos_no_puede_desactivarse", tipo
                )
                omitidos_paquete_incompleto += 1
                continue
            if requiere_pdf_cobranza and not item.get("prestamo_id"):
                log_envio_paquete_incompleto(
                    item_id_log, "sin_prestamo_id_para_pdf_carta", tipo
                )
                omitidos_paquete_incompleto += 1
                continue

        # No reutilizar contexto de otro prestamo (mismo dict en lista, cache de UI, etc.).
        if db and item.get("prestamo_id"):
            ctx_existente = item.get("contexto_cobranza")
            if ctx_existente is not None and not contexto_cobranza_aplica_a_prestamo(
                ctx_existente, item.get("prestamo_id")
            ):
                item.pop("contexto_cobranza", None)
                item.pop("_correlativo_envio", None)

        # Construir contexto_cobranza cuando haga falta: email COBRANZA, adjunto PDF (Carta_Cobranza) o plantilla con variables cobranza
        # Si "Incluir PDF" está marcado pero no hay plantilla (Texto por defecto), igual se construye contexto para adjuntar Carta_Cobranza.pdf
        if (
            db
            and tipo != "MASIVOS"
            and item.get("prestamo_id")
            and not item.get("contexto_cobranza")
        ):
            plantilla = db.get(PlantillaNotificacion, plantilla_id) if plantilla_id else None
            solo_correo_2d = _tipo_dos_dias_antes_solo_correo(tipo)
            need_ctx = (
                (paquete_estricto and not solo_correo_2d)
                or (plantilla and getattr(plantilla, "tipo", None) == "COBRANZA")
                or _cfg_incluir_pdf_anexo(tipo_cfg)
                or (plantilla and plantilla_usa_variables_cobranza(plantilla))
            )
            if need_ctx:
                ctx, corr = build_contexto_cobranza_para_item(
                    db, item, correlativos_en_batch, fecha_referencia=fecha_referencia
                )
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
        # Si el cuerpo es HTML (plantilla editor), enviar como multipart/alternative html.
        # La lista antigua omitia <p>, <ul>, etc.; con adjuntos Gmail mostraba solo texto plano.
        if body_html is None and cuerpo and cuerpo_parece_html(cuerpo):
            body_html = cuerpo
        # Adjuntos obligatorios cuando están seleccionados en Config (Notificaciones → Envíos):
        # - PDF (pestaña 2): Carta_Cobranza.pdf generada desde Plantilla anexo PDF. Se agrega OBLIGATORIAMENTE si incluir_pdf_anexo=True.
        # - Adj. (pestaña 3): Documentos PDF fijos subidos en Documentos PDF anexos. Se agregan OBLIGATORIAMENTE si incluir_adjuntos_fijos no es False.
        if paquete_estricto:
            # Masivos y «2 dias antes»: PDF carta y fijos no son obligatorios; se respetan flags de la fila.
            if tipo == "MASIVOS":
                incluir_pdf_anexo = False
                incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos", True) is not False
            elif _tipo_dos_dias_antes_solo_correo(tipo):
                incluir_pdf_anexo = _cfg_incluir_pdf_anexo(tipo_cfg)
                incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos", True) is not False
            else:
                incluir_pdf_anexo = True
                incluir_adjuntos_fijos = True
        else:
            # Masivos: nunca Carta_Cobranza.pdf aunque la fila tenga PDF marcado (checkbox mora).
            if tipo == "MASIVOS":
                incluir_pdf_anexo = False
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
            if tipo == "MASIVOS" or _tipo_dos_dias_antes_solo_correo(tipo):
                ok_pkg = True
            if not ok_pkg:
                relax_prueba = bool(
                    getattr(settings, "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO", False)
                )
                if relax_prueba and forzar_destinos_prueba is not None:
                    log = logging.getLogger(__name__)
                    log.warning(
                        "[notif_envio_paquete] RELAX_SOLO_PRUEBA_DESTINO: se envia correo de prueba con paquete "
                        "incompleto (%s). No aplica a envios masivos reales.",
                        mot_pkg,
                    )
                else:
                    log_envio_paquete_incompleto(item_id_log, mot_pkg, tipo)
                    omitidos_paquete_incompleto += 1
                    continue

        # Mismo HTML y adjuntos que producción; destino: prueba o cliente.
        if forzar_destinos_prueba is not None:
            to_email = [e.strip() for e in forzar_destinos_prueba if e and isinstance(e, str) and "@" in e.strip()]
            bcc_list = None
        elif usar_solo_pruebas:
            to_email = [email_pruebas]
            cco = tipo_cfg.get("cco") or []
            bcc_list = (
                [
                    e.strip()
                    for e in cco
                    if e and isinstance(e, str) and "@" in e.strip()
                ]
                if isinstance(cco, list)
                else []
            )
            bcc_list = bcc_list or None
        elif bloqueo_pruebas_sin_email:
            to_email = []  # Modo prueba activo pero sin correo de pruebas: no enviar a nadie
            bcc_list = None
        else:
            # Solo correo principal (correo 1). No secundario ni múltiples To (política notificaciones).
            c1 = (item.get("correo_1") or item.get("correo") or "").strip()
            if (not c1 or "@" not in c1) and isinstance(item.get("correos"), list):
                prim = item.get("correos")
                if prim and isinstance(prim[0], str) and prim[0].strip():
                    c1 = prim[0].strip()
            to_email = lista_correo_principal_para_notificaciones(c1)
            cco = tipo_cfg.get("cco") or []
            bcc_list = [e.strip() for e in cco if e and isinstance(e, str) and "@" in e.strip()] if isinstance(cco, list) else []

        email_sent_ok = False
        if to_email:
            tipo_tab_envio = _tipo_tab_para_persistencia(tipo)
            if tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
                tipo_tab_envio = "d_2_antes_vencimiento"
            smtp_meta: dict = {}
            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
                tipo_tab=tipo_tab_envio,
                respetar_destinos_manuales=bool(forzar_destinos_prueba),
                smtp_session_metadata=smtp_meta,
            )
            log_envio_email(item_id_log, to_email[0], ok, None if ok else msg)
            email_sent_ok = ok
            if ok:
                enviados += 1
            else:
                fallidos += 1
            tipo_tab = _tipo_tab_para_persistencia(tipo)
            if tipo_tab:
                adj_snapshot: Optional[List[Tuple[str, bytes]]] = None
                if attachments:
                    adj_snapshot = [(str(n or f"adjunto_{i}.pdf"), bytes(b)) for i, (n, b) in enumerate(attachments) if b]
                    if not adj_snapshot:
                        adj_snapshot = None
                registros_envio.append(
                    (
                        EnvioNotificacion(
                            tipo_tab=tipo_tab,
                            asunto=(asunto or "")[:500] if asunto else None,
                            email=unir_destinatarios_log(to_email, max_len=255),
                            nombre=(item.get("nombre") or "")[:255],
                            cedula=(item.get("cedula") or "")[:50],
                            exito=ok,
                            error_mensaje=None if ok else (msg or "")[:5000],
                            prestamo_id=item.get("prestamo_id"),
                            correlativo=item.get("_correlativo_envio"),
                            mensaje_html=body_html,
                            mensaje_texto=cuerpo if cuerpo else None,
                            metadata_tecnica=smtp_meta if smtp_meta else None,
                        ),
                        adj_snapshot,
                    )
                )
        else:
            if not usar_solo_pruebas:
                sin_email += 1
        # WhatsApp solo si el correo se envio OK (paquete ya validado arriba).
        telefono = (item.get("telefono") or "").strip()
        if telefono and email_sent_ok and forzar_destinos_prueba is None:
            ok, _ = send_whatsapp_text(telefono, cuerpo)
            if ok:
                enviados_whatsapp += 1
            else:
                fallidos_whatsapp += 1
    if registros_envio:
        try:
            for envio_row, adjuntos_snap in registros_envio:
                db.add(envio_row)
                persistir_snapshot_envio_notificacion(db, envio_row, adjuntos_snap)
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
        omitidos_desistimiento=omitidos_desistimiento,
    )
    if enviados == 0 and len(items) > 0:
        log = logging.getLogger(__name__)
        if omitidos_paquete_incompleto > 0 and paquete_estricto:
            log.warning(
                "[notif_envio_diagnostico] enviados=0: %s items omitidos por paquete incompleto "
                "(NOTIFICACIONES_PAQUETE_ESTRICTO=true). Se exige plantilla activa y Carta_Cobranza.pdf "
                "valida (%%PDF), salvo PAGO_2_DIAS_ANTES_PENDIENTE (solo correo). "
                "Emergencia: NOTIFICACIONES_PAQUETE_ESTRICTO=false en .env.",
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
        "omitidos_desistimiento": omitidos_desistimiento,
        "omitidos_paquete_incompleto": omitidos_paquete_incompleto,
        "enviados_whatsapp": enviados_whatsapp,
        "fallidos_whatsapp": fallidos_whatsapp,
    }


# --- Notificaciones previas (5, 3, 1 d�as antes) ---

_FC_Q = Query(
    None,
    description=(
        "Fecha de referencia America/Caracas (YYYY-MM-DD). Listado/envio como si fuera ese dia. "
        "Omitir = hoy en Caracas."
    ),
)


@router_previas.get("")
def get_notificaciones_previas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones previas: cuotas que vencen en 5, 3 o 1 d�a. Verifica c�dula y email en tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
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
def enviar_notificaciones_previas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente en notificaciones previas. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
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
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_previas,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones previas finalizado.", **res}


# --- D�a de pago (vence hoy) ---

@router_dia_pago.get("")
def get_notificaciones_dia_pago(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones del d�a de pago: cuotas que vencen hoy. Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = data["hoy"]
    return {"items": items, "total": len(items)}


def _tipo_dia_pago(_item: dict) -> str:
    return "PAGO_DIA_0"


def _tipo_pago_2_dias_antes_pendiente(_item: dict) -> str:
    return "PAGO_2_DIAS_ANTES_PENDIENTE"


@router_dia_pago.post("/enviar")
def enviar_notificaciones_dia_pago(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente con cuota que vence hoy. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
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
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_dia_pago,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones d�a de pago finalizado.", **res}


# --- Notificaciones retrasadas (1, 3, 5 d�as atrasado) ---

@router_retrasadas.get("")
def get_notificaciones_retrasadas(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de notificaciones retrasadas: cuotas con 1, 3 o 5 d�as de atraso. Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = (
        data["dias_1_retraso"]
        + data["dias_3_retraso"]
        + data["dias_5_retraso"]
        + data["dias_30_retraso"]
    )
    return {
        "items": items,
        "total": len(items),
        "dias_1": len(data["dias_1_retraso"]),
        "dias_3": len(data["dias_3_retraso"]),
        "dias_5": len(data["dias_5_retraso"]),
        "dias_30": len(data["dias_30_retraso"]),
    }


def _tipo_retrasadas(item: dict) -> str:
    d = item.get("dias_atraso")
    return {
        1: "PAGO_1_DIA_ATRASADO",
        3: "PAGO_3_DIAS_ATRASADO",
        5: "PAGO_5_DIAS_ATRASADO",
        30: "PAGO_30_DIAS_ATRASADO",
    }.get(d, "PAGO_1_DIA_ATRASADO")


@router_retrasadas.post("/enviar")
def enviar_notificaciones_retrasadas(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente con cuota retrasada. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    data = get_notificaciones_tabs_data(db, fecha_referencia=fecha_ref)
    items = (
        data["dias_1_retraso"]
        + data["dias_3_retraso"]
        + data["dias_5_retraso"]
        + data["dias_30_retraso"]
    )
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
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_retrasadas,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones retrasadas finalizado.", **res}


# --- Notificaciones prejudiciales (5+ cuotas en VENCIDO o MORA) ---

@router_prejudicial.get("")
def get_notificaciones_prejudicial(
    estado: str = None,
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Lista de clientes con 5+ cuotas en estado VENCIDO o MORA (prejudicial). Email desde tabla clientes."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)
    return {"items": items, "total": len(items)}


def _tipo_prejudicial(_item: dict) -> str:
    return "PREJUDICIAL"


@router_prejudicial.post("/enviar")
def enviar_notificaciones_prejudicial(
    fecha_caracas: Optional[str] = _FC_Q,
    db: Session = Depends(get_db),
):
    """Env�a correo a cada cliente en situaci�n prejudicial. Respeta config env�os (habilitado/CCO) desde BD."""
    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)
    config_envios = get_notificaciones_envios_config(db)
    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)
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
    res = _enviar_correos_items(
        items,
        asunto,
        cuerpo,
        config_envios,
        _tipo_prejudicial,
        db,
        fecha_referencia=fecha_ref,
    )
    return {"mensaje": "Env�o de notificaciones prejudiciales finalizado.", **res}


def get_items_masivos(db: Session) -> List[dict]:
    """
    Contactos para comunicaciones masivas.

    Fuente principal: vista vw_notificaciones_masivos_contactos (sincronizada en 2 vias).
    Fallback de compatibilidad: tabla clientes si la vista aun no existe.
    """
    items: List[dict] = []

    try:
        rows = db.execute(
            text(
                """
                SELECT id, cliente_id, cedula, nombre, email, email_secundario, telefono, updated_at
                FROM vw_notificaciones_masivos_contactos
                ORDER BY nombre ASC, id ASC
                """
            )
        ).mappings().all()
        for r in rows:
            em = str(r.get("email") or "").strip() or None
            correos = lista_correo_principal_para_notificaciones(em)
            if not correos:
                continue
            items.append(
                {
                    "cliente_id": r.get("cliente_id"),
                    "nombre": r.get("nombre") or "",
                    "cedula": r.get("cedula") or "",
                    "correo_1": correos[0],
                    "correo_2": None,
                    "correo": correos[0],
                    "correos": correos,
                    "telefono": str(r.get("telefono") or "").strip(),
                    "estado": "COMUNICACION_GENERAL",
                }
            )
        return [
            it
            for it in items
            if not cliente_tiene_prestamo_desistimiento(db, it.get("cliente_id"))
        ]
    except Exception:
        logger.warning(
            "get_items_masivos: vista vw_notificaciones_masivos_contactos no disponible; usando fallback clientes",
            exc_info=True,
        )

    rows = (
        db.execute(
            select(Cliente)
            .where(Cliente.email.isnot(None), func.length(func.trim(Cliente.email)) > 0)
            .order_by(Cliente.nombres.asc(), Cliente.id.asc())
        )
        .scalars().all()
    )
    for c in rows:
        correos = lista_correo_principal_notificaciones_desde_objeto(c)
        if not correos:
            continue
        items.append(
            {
                "cliente_id": c.id,
                "nombre": c.nombres or "",
                "cedula": c.cedula or "",
                "correo_1": correos[0],
                "correo_2": None,
                "correo": correos[0],
                "correos": correos,
                "telefono": (getattr(c, "telefono", None) or "").strip(),
                "estado": "COMUNICACION_GENERAL",
            }
        )
    return [
        it
        for it in items
        if not cliente_tiene_prestamo_desistimiento(db, it.get("cliente_id"))
    ]


def _tipo_masivos(_item: dict) -> str:
    return "MASIVOS"


def _normalizar_campana_masiva(raw: dict, idx: int) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    camp_id = str(raw.get("id") or f"campana-{idx}").strip() or f"campana-{idx}"
    nombre = str(raw.get("nombre") or f"Campana {idx}").strip() or f"Campana {idx}"
    cco_raw = raw.get("cco")
    cco = [str(e).strip() for e in cco_raw] if isinstance(cco_raw, list) else []
    cco = [e for e in cco if e]
    dias_raw = raw.get("dias_semana")
    dias = []
    if isinstance(dias_raw, list):
        for d in dias_raw:
            try:
                v = int(d)
            except (TypeError, ValueError):
                continue
            if 0 <= v <= 6:
                dias.append(v)
    dias = sorted(set(dias))
    return {
        "id": camp_id,
        "nombre": nombre,
        "habilitado": raw.get("habilitado", True) is not False,
        "plantilla_id": raw.get("plantilla_id"),
        "programador": str(raw.get("programador") or "03:00"),
        "cco": cco,
        "dias_semana": dias,
    }


def get_campanas_masivos_config(config_envios: dict) -> List[dict]:
    raw = config_envios.get("masivos_campanas") if isinstance(config_envios, dict) else None
    if not isinstance(raw, list):
        return []
    return [_normalizar_campana_masiva(c, i + 1) for i, c in enumerate(raw)]


def _norm_cco_list(raw) -> List[str]:
    if not isinstance(raw, list):
        return []
    return [
        str(e).strip()
        for e in raw
        if e and isinstance(e, str) and "@" in str(e).strip()
    ]


def _tipo_cfg_masivos_por_campana(camp: dict, config_envios: dict) -> dict:
    """
    Combina la fila global MASIVOS (tabla de envios) con cada campaña en masivos_campanas.

    La UI guarda plantilla/CCO en la fila «Comunicaciones masivas» y puede repetirlos
    por campaña; si la campaña no tiene plantilla_id, debe usarse el de la fila MASIVOS
    (antes solo se leía camp.plantilla_id y se ignoraba la selección principal).
    """
    base_m = (
        config_envios.get("MASIVOS")
        if isinstance(config_envios.get("MASIVOS"), dict)
        else {}
    )
    cid = _parse_plantilla_id_desde_config(camp.get("plantilla_id"))
    bid = _parse_plantilla_id_desde_config(base_m.get("plantilla_id"))
    plantilla_efectiva = cid if cid else bid

    cco_c = _norm_cco_list(camp.get("cco"))
    cco_b = _norm_cco_list(base_m.get("cco"))
    cco = cco_c if len(cco_c) > 0 else cco_b

    incluir_adj = base_m.get("incluir_adjuntos_fijos", True) is not False

    return {
        "habilitado": True,
        "cco": cco,
        "plantilla_id": plantilla_efectiva,
        "programador": camp.get("programador") or base_m.get("programador") or "03:00",
        "incluir_pdf_anexo": False,
        "incluir_adjuntos_fijos": incluir_adj,
    }


def ejecutar_envio_masivos_por_campanas(
    db: Session,
    config_envios: dict,
    *,
    forzar_habilitado: bool = False,
) -> dict:
    campanas = get_campanas_masivos_config(config_envios)
    base_m_row = (
        config_envios.get("MASIVOS")
        if isinstance(config_envios.get("MASIVOS"), dict)
        else {}
    )
    if not campanas and (
        forzar_habilitado or base_m_row.get("habilitado", True) is not False
    ):
        campanas = [
            _normalizar_campana_masiva(
                {
                    "id": "fila-principal-masivos",
                    "nombre": "Masivos (fila principal)",
                    "habilitado": True,
                    "plantilla_id": base_m_row.get("plantilla_id"),
                    "programador": base_m_row.get("programador") or "03:00",
                    "cco": base_m_row.get("cco")
                    if isinstance(base_m_row.get("cco"), list)
                    else [],
                    "dias_semana": [],
                },
                0,
            )
        ]
    items = get_items_masivos(db)
    base_asunto = "Comunicado oficial - Rapicredit"
    base_cuerpo = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )

    total_enviados = total_fallidos = total_sin_email = 0
    total_omitidos_config = total_omitidos_paquete = 0
    total_wok = total_wf = 0
    detalles: Dict[str, dict] = {}

    for camp in campanas:
        if not camp.get("habilitado", True) and not forzar_habilitado:
            continue

        tipo_cfg = _tipo_cfg_masivos_por_campana(camp, config_envios)
        cfg_tmp = dict(config_envios)
        cfg_tmp["MASIVOS"] = tipo_cfg

        r = _enviar_correos_items(items, base_asunto, base_cuerpo, cfg_tmp, _tipo_masivos, db)
        detalles[str(camp.get("id") or camp.get("nombre") or "campana")] = {
            "campana": camp,
            **r,
        }
        total_enviados += int(r.get("enviados", 0) or 0)
        total_fallidos += int(r.get("fallidos", 0) or 0)
        total_sin_email += int(r.get("sin_email", 0) or 0)
        total_omitidos_config += int(r.get("omitidos_config", 0) or 0)
        total_omitidos_paquete += int(r.get("omitidos_paquete_incompleto", 0) or 0)
        total_wok += int(r.get("enviados_whatsapp", 0) or 0)
        total_wf += int(r.get("fallidos_whatsapp", 0) or 0)

    return {
        "enviados": total_enviados,
        "fallidos": total_fallidos,
        "sin_email": total_sin_email,
        "omitidos_config": total_omitidos_config,
        "omitidos_paquete_incompleto": total_omitidos_paquete,
        "enviados_whatsapp": total_wok,
        "fallidos_whatsapp": total_wf,
        "total_en_lista": len(items),
        "campanas": detalles,
    }


@router_masivos.get("")
def get_notificaciones_masivos(db: Session = Depends(get_db)):
    """Lista de clientes para comunicaciones masivas (sin relacion con mora/pagos)."""
    items = get_items_masivos(db)
    return {"items": items, "total": len(items)}


@router_masivos.post("/enviar")
def enviar_notificaciones_masivos(db: Session = Depends(get_db)):
    """Envia comunicaciones masivas segun campanas configuradas para MASIVOS."""
    config_envios = get_notificaciones_envios_config(db)
    res = ejecutar_envio_masivos_por_campanas(db, config_envios, forzar_habilitado=True)
    return {"mensaje": "Envio de notificaciones masivas finalizado.", **res}


# Tipos alineados con CRITERIOS_ENVIO_TABLA (frontend) y _CONFIG_TIPO_TO_TAB
TIPOS_CASO_MANUAL = frozenset(
    {
        "PAGO_5_DIAS_ANTES",
        "PAGO_3_DIAS_ANTES",
        "PAGO_1_DIA_ANTES",
        "PAGO_2_DIAS_ANTES_PENDIENTE",
        "PAGO_DIA_0",
        "PAGO_1_DIA_ATRASADO",
        "PAGO_3_DIAS_ATRASADO",
        "PAGO_5_DIAS_ATRASADO",
        "PAGO_30_DIAS_ATRASADO",
        "PREJUDICIAL",
        "MASIVOS",
    }
)


def _config_envios_forzar_habilitado_caso(config_envios: dict, tipo: str) -> dict:
    """
    Copia superficial de la config de envios con habilitado=True solo para el tipo indicado.
    El envio manual y la prueba de paquete deben ejecutarse aunque el toggle Envio este apagado.
    """
    out = dict(config_envios)
    cur = out.get(tipo)
    merged = dict(cur) if isinstance(cur, dict) else {}
    merged["habilitado"] = True
    out[tipo] = merged
    return out


def _resolver_tipo_envio_manual_fijo(tipo_caso: str) -> Callable[[dict], str]:
    """
    POST /notificaciones/enviar-caso-manual debe usar siempre la misma clave de configuracion
    (plantilla, CCO, PDFs, tipo_tab) para todos los destinatarios del lote, la del caso elegido.

    No usar _tipo_previas / _tipo_retrasadas aqui: infieren por dias_antes_vencimiento / dias_atraso
    de cada fila y pueden mezclar PAGO_1_DIA_ANTES con PAGO_3_DIAS_ATRASADO, etc.
    """

    def _inner(_item: dict) -> str:
        return tipo_caso

    return _inner


def ejecutar_envio_caso_manual(
    db: Session,
    tipo: str,
    fecha_referencia: Optional[date] = None,
) -> dict:
    """
    Envio sincrono solo para un criterio (una fila de configuracion: PAGO_1_DIA_ANTES, etc.).
    No programa tareas en segundo plano ni dispara otros casos: un solo tipo por peticion.

    Lista de destinatarios = la misma regla que la pestaña correspondiente; cada correo usa
    unicamente la config de ese tipo (plantilla/CCO/PDF del caso), sin inferir otro tipo por fila.

    fecha_referencia: mismo criterio que ?fecha_caracas= en GET listados (America/Caracas).
    """
    tipo = (tipo or "").strip()
    if tipo not in TIPOS_CASO_MANUAL:
        raise ValueError("tipo_caso_manual_invalido")

    config_raw = get_notificaciones_envios_config(db)
    config_envios = _config_envios_forzar_habilitado_caso(config_raw, tipo)

    asunto_prev = "Recordatorio: cuota por vencer - Rapicredit"
    cuerpo_prev = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota por vencer.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago a tiempo.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_hoy = "Vencimiento hoy: cuota de pago - Rapicredit"
    cuerpo_hoy = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le informamos que su cuota vence HOY.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor realice el pago hoy.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_ret = "Cuenta con cuota atrasada - Rapicredit"
    cuerpo_ret = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le recordamos que tiene una cuota en mora.\n"
        "Fecha de vencimiento: {fecha_vencimiento}\n"
        "N\u00famero de cuota: {numero_cuota}\n"
        "Monto: {monto}\n\n"
        "Por favor regularice su pago lo antes posible.\n\n"
        "Saludos,\nRapicredit"
    )
    asunto_prej = "Aviso prejudicial - Rapicredit"
    asunto_mas = "Comunicado oficial - Rapicredit"
    cuerpo_prej = (
        "Estimado/a {nombre} (c\u00e9dula {cedula}),\n\n"
        "Le informamos que su cuenta presenta varias cuotas en mora.\n"
        "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
        "Cuota de referencia: {numero_cuota}\n"
        "Monto de referencia: {monto}\n\n"
        "Por favor contacte a la entidad para regularizar su situaci\u00f3n.\n\n"
        "Saludos,\nRapicredit"
    )
    cuerpo_mas = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )

    ref = fecha_referencia
    if tipo == "PREJUDICIAL":
        items = build_prejudicial_items(db, fecha_referencia=ref)
        res = _enviar_correos_items(
            items,
            asunto_prej,
            cuerpo_prej,
            config_envios,
            _resolver_tipo_envio_manual_fijo("PREJUDICIAL"),
            db,
            fecha_referencia=ref,
        )
    elif tipo == "MASIVOS":
        items = get_items_masivos(db)
        res = ejecutar_envio_masivos_por_campanas(db, config_envios, forzar_habilitado=True)
    else:
        data = get_notificaciones_tabs_data(db, fecha_referencia=ref)
        if tipo == "PAGO_5_DIAS_ANTES":
            items = data["dias_5"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_5_DIAS_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_3_DIAS_ANTES":
            items = data["dias_3"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_3_DIAS_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_1_DIA_ANTES":
            items = data["dias_1"]
            res = _enviar_correos_items(
                items,
                asunto_prev,
                cuerpo_prev,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_1_DIA_ANTES"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
            items = build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=ref)
            res = _enviar_correos_items(
                items,
                ASUNTO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
                CUERPO_DEFAULT_PAGO_2_DIAS_ANTES_PENDIENTE,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_2_DIAS_ANTES_PENDIENTE"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_DIA_0":
            items = data["hoy"]
            res = _enviar_correos_items(
                items,
                asunto_hoy,
                cuerpo_hoy,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_DIA_0"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_1_DIA_ATRASADO":
            items = data["dias_1_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_1_DIA_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_3_DIAS_ATRASADO":
            items = data["dias_3_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_3_DIAS_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_5_DIAS_ATRASADO":
            items = data["dias_5_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_5_DIAS_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        elif tipo == "PAGO_30_DIAS_ATRASADO":
            items = data["dias_30_retraso"]
            res = _enviar_correos_items(
                items,
                asunto_ret,
                cuerpo_ret,
                config_envios,
                _resolver_tipo_envio_manual_fijo("PAGO_30_DIAS_ATRASADO"),
                db,
                fecha_referencia=ref,
            )
        else:
            raise ValueError("tipo_caso_manual_invalido")

    return {
        "mensaje": f"Envio manual del caso {tipo} finalizado.",
        "tipo_caso": tipo,
        "total_en_lista": len(items),
        **res,
    }


def ejecutar_envio_todas_notificaciones(db: Session) -> dict:
    """
    Ejecuta en un solo batch varias familias de notificacion: previas, dia de pago, retrasadas,
    prejudicial y masivos. Cada tipo usa su propia configuracion en notificaciones_envios (habilitado,
    CCO, modo pruebas, etc.); no se mezclan entre si.

    No incluye PAGO_2_DIAS_ANTES_PENDIENTE (2 dias antes del vencimiento), que tiene envio propio.

    Solo desde POST /notificaciones/enviar-todas (BackgroundTasks); sin envio automatico por hora.
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
    items_retrasadas = (
        data["dias_1_retraso"]
        + data["dias_3_retraso"]
        + data["dias_5_retraso"]
        + data["dias_30_retraso"]
    )
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

    # Masivos (comunicaciones generales): misma plantilla/CCO que campañas + fila MASIVOS.
    # enviar-todas y "Envios masivos prueba" leian solo config["MASIVOS"] e ignoraban
    # plantilla_id en masivos_campanas; se unifica con _tipo_cfg_masivos_por_campana.
    items_masivos = get_items_masivos(db)
    asunto_mas = "Comunicado oficial - Rapicredit"
    cuerpo_mas = (
        "Estimado/a {nombre} (cedula {cedula}),\n\n"
        "Le compartimos este comunicado oficial de Rapicredit.\n"
        "Revise el contenido completo en este correo.\n\n"
        "Saludos,\nRapicredit"
    )
    campanas_m = get_campanas_masivos_config(config_envios)
    hab_m = [c for c in campanas_m if c.get("habilitado", True) is not False]
    if hab_m:
        camp_m_ref = hab_m[0]
    else:
        camp_m_ref = _normalizar_campana_masiva(
            {
                "id": "enviar-todas-masivos",
                "nombre": "Masivos",
                "habilitado": True,
                "plantilla_id": None,
                "programador": "03:00",
                "cco": [],
                "dias_semana": [],
            },
            0,
        )
    tipo_mas_merge = _tipo_cfg_masivos_por_campana(camp_m_ref, config_envios)
    cfg_masivos_envio = dict(config_envios)
    cfg_masivos_envio["MASIVOS"] = tipo_mas_merge
    r = _enviar_correos_items(
        items_masivos, asunto_mas, cuerpo_mas, cfg_masivos_envio, _tipo_masivos, db
    )
    total_enviados += r.get("enviados", 0)
    total_fallidos += r.get("fallidos", 0)
    total_sin_email += r.get("sin_email", 0)
    total_omitidos_config += r.get("omitidos_config", 0)
    total_omitidos_paquete += r.get("omitidos_paquete_incompleto", 0)
    total_whatsapp_ok += r.get("enviados_whatsapp", 0)
    total_whatsapp_fail += r.get("fallidos_whatsapp", 0)
    detalles["masivos"] = r

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
