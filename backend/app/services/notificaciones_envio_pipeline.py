"""
Núcleo de envío de notificaciones por ítem (email/WhatsApp, adjuntos, paquete estricto).

Extraído de ``notificaciones_tabs.routes`` para mantener routers como delegación fina
y facilitar pruebas unitarias sobre el pipeline sin montar FastAPI.
"""
import logging
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import cuerpo_parece_html, send_email
from app.core.email_config_holder import sync_from_db as sync_email_config_from_db
from app.core.whatsapp_send import send_whatsapp_text
from app.api.v1.endpoints.notificaciones.routes import (
    build_contexto_cobranza_para_item,
    contexto_cobranza_aplica_a_prestamo,
    get_plantilla_asunto_cuerpo,
    plantilla_usa_variables_cobranza,
)
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.services.envio_notificacion_snapshot import persistir_snapshot_envio_notificacion
from app.services.notificaciones_envios_store import coerce_modo_pruebas_notificaciones
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_tiene_prestamo_desistimiento,
)
from app.services.carta_cobranza_pdf import generar_carta_cobranza_pdf
from app.services.adjunto_fijo_cobranza import get_adjunto_fijo_cobranza_bytes, get_adjuntos_fijos_por_caso
from app.services.notificacion_service import alinear_items_contacto_titular_prestamo
from app.utils.cliente_emails import (
    lista_correo_principal_para_notificaciones,
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

logger = logging.getLogger(__name__)
# Mapeo tipo config (PAGO_5_DIAS_ANTES, etc.) a tipo_tab para estad�sticas/rebotados (solo los 5 que muestra la UI)
_CONFIG_TIPO_TO_TAB = {
    "PAGO_5_DIAS_ANTES": "dias_5",
    "PAGO_3_DIAS_ANTES": "dias_3",
    "PAGO_1_DIA_ANTES": "dias_1",
    "PAGO_2_DIAS_ANTES_PENDIENTE": "d_2_antes_vencimiento",
    "PAGO_DIA_0": "hoy",
    "PAGO_1_DIA_ATRASADO": "dias_1_retraso",
    "PAGO_10_DIAS_ATRASADO": "dias_10_retraso",
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
    # Solo filas de criterio (PAGO_*, PREJUDICIAL, MASIVOS, COBRANZA, …); no contar cron ni masivos_campanas.
    _keys_no_fila_envio = frozenset(
        {
            "modo_pruebas",
            "email_pruebas",
            "emails_pruebas",
            "masivos_campanas",
            "cron_envio_pago_2_dias_antes",
        }
    )
    habilitados = sum(
        1
        for k, v in config_envios.items()
        if k not in _keys_no_fila_envio
        and isinstance(v, dict)
        and v.get("habilitado", True) is not False
    )
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
    if db:
        alinear_items_contacto_titular_prestamo(db, items)
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

