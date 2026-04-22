"""
Orquestacion: Gmail -> Gemini/BD por **cada adjunto elegible** (remitente en clientes, o **Plan B** Mercantil/BNC si el De no está en BD), una fila Excel/BD por comprobante OK.
  -> flush sync_item + temporal -> comprobante en pago_comprobante_imagen (reuso por SHA-256 en la misma corrida) + URL en drive_link -> un solo commit; si falla el binario, rollback de esas filas.
  No hay subidas a Google Drive: el comprobante queda en BD; no se archiva .eml en Drive (drive_email_link sin uso).
  Si no cumple plantillas 1/2/3/4 o faltan datos -> no fila ni comprobante en BD para ese adjunto.

**Re-proceso innegociable:** si el mensaje tiene **cualquier etiqueta de usuario** Gmail (API ``type=user``), el pipeline **no** vuelve a escanear ni reetiqueta. Se hace *skip total* (sin nuevas filas Excel/BD), preservando la etiqueta existente.

**Regla estricta (1 página por binario):** solo se digitaliza **una página** por archivo: imágenes tal cual; PDF solo si tiene **exactamente 1 página**. PDF con **2+ páginas** no se envía a Gemini; el hilo recibe etiqueta Gmail **PAGINAS** (puede convivir con otras etiquetas del mismo paso salvo la regla exclusiva de ERROR EMAIL abajo).

**Regla de decisión actual (sin ambigüedad):**
- Paso 1: si en el correo hay digitalización OK de plantilla A/B, etiqueta final = MERCANTIL o BNC.
- Paso 2: si no hubo A/B y el remitente está en `clientes`, se admite C/D y etiqueta final = BINANCE o BNV.
- Paso 3 (fallback): TEXTO -> MASTER -> ERROR EMAIL -> MANUAL.
- Solo se aplica **una** etiqueta final por correo (set permitido arriba), sin etiquetas auxiliares.

**Remitente y Plan B:**
- Remitente en `clientes`: se evalúan plantillas según prompts/reglas de negocio.
- Remitente fuera de `clientes` (Plan B): solo A/B con cédula desde imagen; C/D/NR no aplican.
- `master@rapicreditca.com` sin digitalización válida cae en fallback MASTER; sin fila en clientes fuera de ese caso, fallback ERROR EMAIL.

Excel de revisión y negocio:
- `pagos_gmail_sync_item` / `gmail_temporal` guardan cada comprobante válido de extracción.
- Alta automática (A-D/NR) y cascada de cuotas se evalúan en servicios de negocio.
- Los casos no autoconciliados permanecen para revisión manual en exportes de Gmail.
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional


def _finished_at_naive_utc() -> datetime:
    """Columnas pagos_gmail_sync.* son DateTime(timezone=False); naive UTC evita ambigüedad en drivers."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal


def _metricas_resumen_corrida_gmail_pagos(db: Session, sync_id: int) -> dict[str, int]:
    """
    Comprobantes insertados en esta sync vs altas automáticas exitosas (traza con pago_id).
    Los pendientes de revisión / Excel ≈ comprobantes - válidos.
    """
    from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza

    n_items = int(
        db.scalar(
            select(func.count())
            .select_from(PagosGmailSyncItem)
            .where(PagosGmailSyncItem.sync_id == sync_id)
        )
        or 0
    )
    n_valid = int(
        db.scalar(
            select(func.count())
            .select_from(PagosGmailAbcdCuotasTraza)
            .where(
                PagosGmailAbcdCuotasTraza.sync_id == sync_id,
                PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
            )
        )
        or 0
    )
    n_sin_cuotas = int(
        db.scalar(
            select(func.count())
            .select_from(PagosGmailAbcdCuotasTraza)
            .where(
                PagosGmailAbcdCuotasTraza.sync_id == sync_id,
                PagosGmailAbcdCuotasTraza.etapa_final == "PAGO_SIN_CUOTAS",
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
            )
        )
        or 0
    )
    n_invalid = max(0, n_items - n_valid)
    return {
        "comprobantes_digitados": n_items,
        "pagos_validos_alta_automatica": n_valid,
        "pagos_sin_aplicacion_cuotas": n_sin_cuotas,
        "pagos_invalidos_pendientes_revision": n_invalid,
    }


def _persistir_estado_sync_pipeline_terminal(
    db: Session,
    *,
    sync_id: int,
    status: str,
    emails_ok: int,
    files_ok: int,
    correos_marcados_revision: int,
    run_summary: dict,
    error_message: Optional[str],
) -> None:
    """
    Persiste cierre de corrida en una sola sentencia UPDATE.
    Evita filas success con finished_at NULL cuando la instancia ORM `sync` queda
    desalineada tras muchos commit/rollback en el mismo Session.
    """
    res = db.execute(
        update(PagosGmailSync)
        .where(PagosGmailSync.id == sync_id)
        .values(
            finished_at=_finished_at_naive_utc(),
            status=status,
            emails_processed=emails_ok,
            files_processed=files_ok,
            correos_marcados_revision=correos_marcados_revision,
            run_summary=run_summary,
            error_message=error_message,
        )
    )
    rc = int(getattr(res, "rowcount", -1) or -1)
    if rc != 1:
        logging.getLogger(__name__).warning(
            "[PAGOS_GMAIL] Cierre sync: UPDATE rowcount=%s (esperado 1) sync_id=%s status=%s",
            rc,
            sync_id,
            status,
        )
    db.commit()
    # Evita instancia ORM `sync` (status=running en memoria) confundiendo flush posterior en la misma sesión.
    db.expire_all()
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.gmail_abcd_cuotas_traza import (
    registrar_traza_gmail_abcd_cuotas_evento,
)
from app.services.pagos_gmail.gmail_pipeline_evento import (
    EVT_CAMPOS_INCOMPLETOS_PLANTILLA,
    EVT_ERROR_PROCESAR_ADJUNTO,
    EVT_NO_PLANTILLA_GEMINI,
    EVT_OMISION_ETIQUETA_USUARIO,
    EVT_REMITENTE_INVALIDO,
    EVT_REMITENTE_NO_CLIENTE_CON_MEDIA,
    EVT_SIN_ADJUNTOS_DIGITABLES,
    EVT_SOLO_PDF_MULTIPAGINA,
    registrar_pagos_gmail_pipeline_evento,
)
from app.services.pagos_gmail.pago_abcd_auto_service import (
    crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd,
)
from app.services.pagos_gmail.pago_nr_auto_service import (
    crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr,
)
from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    es_plantilla_banco_abcd,
    item_sync_abcd_candidato_revision_duplicado,
    item_sync_nr_candidato_revision_duplicado,
    resumen_log_linea_plantilla_abcd,
)
from app.services.pagos_gmail.gmail_service import (
    add_message_user_labels_only,
    build_gmail_service,
    ensure_user_label_id,
    invalidate_gmail_labels_list_cache,
    get_pagos_gmail_image_pdf_files_for_pipeline,
    get_message_date,
    get_message_full_payload,
    get_or_create_pagos_gmail_plantilla_label_ids,
    list_gmail_user_label_ids,
    list_messages_by_filter,
    mark_as_read,
    PagosGmailGmailListError,
    PAGOS_GMAIL_LABEL_ERROR_EMAIL,
    PAGOS_GMAIL_LABEL_MANUAL,
    PAGOS_GMAIL_LABEL_MASTER,
    PAGOS_GMAIL_LABEL_IMAGEN_1,
    PAGOS_GMAIL_LABEL_IMAGEN_2,
    PAGOS_GMAIL_LABEL_IMAGEN_3,
    PAGOS_GMAIL_LABEL_IMAGEN_4,
    PAGOS_GMAIL_LABEL_TEXTO,
)
from app.services.pagos_gmail.gemini_service import (
    classify_and_extract_pagos_gmail_attachment,
    PAGOS_GMAIL_FORMATOS_PLANTILLA,
    PAGOS_NA,
)
from app.services.pagos_gmail.pdf_pages import expand_pipeline_pdf_tuples
from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    formatear_cedula,
    get_sheet_name_for_date,
    normalizar_fecha_pago,
    normalizar_referencia,
    resolve_banco_para_excel_pagos_gmail,
)
from app.services.pagos_gmail.comprobante_bd import persistir_comprobante_gmail_en_bd

logger = logging.getLogger(__name__)


def _dedupe_messages_pagos_gmail(raw_messages: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    out: list[dict] = []
    for m in raw_messages:
        mid = m["id"]
        if mid in seen_ids:
            continue
        seen_ids.add(mid)
        out.append(m)
    return out


def _sort_key_pagos_gmail_chrono(m: dict) -> tuple:
    """
    Clave de orden por recepcion (epoch ms Gmail + id estable).
    Prioriza **internal_date_ms** de Gmail (recepcion en servidor); si falta, cabecera Date -> epoch ms UTC;
    empate estable por id de mensaje. Gmail no garantiza orden en messages.list: el pipeline siempre ordena el lote completo.
    """

    def _header_date_to_epoch_ms() -> int:
        h = m.get("headers") or {}
        dt = get_message_date(h)
        try:
            from datetime import timezone as _tz

            if getattr(dt, "tzinfo", None) is None:
                d = dt.replace(tzinfo=_tz.utc)
            else:
                d = dt.astimezone(_tz.utc)
            return int(d.timestamp() * 1000)
        except Exception:
            return 0

    ms = int(m.get("internal_date_ms") or 0)
    if ms <= 0:
        ms = _header_date_to_epoch_ms()
    mid = m.get("id") or ""
    return (ms, mid)


def _sort_messages_inbox_primero_a_ultimo(messages: list[dict]) -> list[dict]:
    """
    Orden estable como bandeja Gmail tipica (arriba = mas reciente): primero el de mayor internalDate,
    al final el mas antiguo. Asi el escaneo recorre del primero al ultimo de esa lista en cada corrida.
    """
    return sorted(messages, key=_sort_key_pagos_gmail_chrono, reverse=True)


# Columna Excel "Banco" al digitalizar: imagen 1 (A) / imagen 2 (B) / imagen 3 Binance (C) / imagen 4 BDV (D).
PAGOS_GMAIL_BANCO_IMAGEN_1 = "Mercantil"
PAGOS_GMAIL_BANCO_IMAGEN_2 = "BNC"
PAGOS_GMAIL_BANCO_IMAGEN_3 = "BINANCE"
PAGOS_GMAIL_BANCO_IMAGEN_4 = "BDV"

# Columna Cedula en Excel cuando no se puede resolver por remitente (max 50 chars en modelo).
PAGOS_GMAIL_ERROR_CEDULA_EMAIL = "ERROR EMAIL"  # sin fila en clientes o fallo al consultar tabla clientes
# Re-escaneo ERROR EMAIL (Mercantil/BNC): cédula ilegible en imagen — literal en Excel (no confundir con ERROR EMAIL).
PAGOS_GMAIL_ERROR_CEDULA_IMAGEN = "ERROR"

# De / From en minusculas: Gmail solo etiqueta MASTER (no plantilla 1-4 ni ERROR EMAIL).
PAGOS_GMAIL_SENDER_MASTER = "master@rapicreditca.com"
PAGOS_GMAIL_ETIQUETAS_FINALES_PERMITIDAS = frozenset(
    {
        PAGOS_GMAIL_LABEL_IMAGEN_1,
        PAGOS_GMAIL_LABEL_IMAGEN_2,
        PAGOS_GMAIL_LABEL_IMAGEN_3,
        PAGOS_GMAIL_LABEL_IMAGEN_4,
        PAGOS_GMAIL_LABEL_ERROR_EMAIL,
        PAGOS_GMAIL_LABEL_MANUAL,
        PAGOS_GMAIL_LABEL_MASTER,
        PAGOS_GMAIL_LABEL_TEXTO,
    }
)


def _cedula_por_email_cliente(db: Session, email_raw: str) -> tuple[Optional[str], Optional[str]]:
    """
    Devuelve (cedula_raw, motivo_fallo).
    motivo_fallo: None si hay cedula; "EMAIL" sin coincidencia; "BD" si la consulta lanzo excepcion.
    Orden fijo: primero `clientes.email` (correo principal), si no hay fila entonces `clientes.email_secundario`.
    """
    em = (email_raw or "").strip().lower()
    if not em:
        return None, "EMAIL"
    try:
        row = db.execute(
            select(Cliente.cedula)
            .where(func.lower(func.trim(Cliente.email)) == em)
            .limit(1)
        ).scalar_one_or_none()
        if row:
            return row, None
        row_sec = db.execute(
            select(Cliente.cedula)
            .where(Cliente.email_secundario.isnot(None))
            .where(func.trim(Cliente.email_secundario) != "")
            .where(func.lower(func.trim(Cliente.email_secundario)) == em)
            .limit(1)
        ).scalar_one_or_none()
        if row_sec:
            return row_sec, None
        return None, "EMAIL"
    except Exception as ex:
        logger.warning("[PAGOS_GMAIL] Lookup cedula por email clientes: %s", ex)
        return None, "BD"


def _cedula_desde_imagen_rescan_error_email(raw: Optional[str]) -> str:
    """
    Re-escaneo ERROR EMAIL (solo plantillas A/B): cédula leída de la imagen por Gemini.
    Si no es claramente válida (V/E/J + dígitos), devuelve PAGOS_GMAIL_ERROR_CEDULA_IMAGEN.
    """
    s = (raw or "").strip()
    if not s or s.upper() in (PAGOS_NA, "NA"):
        return PAGOS_GMAIL_ERROR_CEDULA_IMAGEN
    if s.upper() == "ERROR":
        return PAGOS_GMAIL_ERROR_CEDULA_IMAGEN
    fc = formatear_cedula(s)
    if not fc or fc.upper() == PAGOS_NA:
        return PAGOS_GMAIL_ERROR_CEDULA_IMAGEN
    if re.match(r"^[VEJ]\d{5,12}$", fc, re.IGNORECASE):
        return fc[0].upper() + fc[1:]
    return PAGOS_GMAIL_ERROR_CEDULA_IMAGEN


def _cedula_columna_desde_remitente(
    db: Session, sender_lc: str
) -> tuple[str, bool]:
    """
    Devuelve (valor columna cedula, es_cliente_valido).
    Si hay cliente con `email` o `email_secundario` = remitente (tras normalizar): cedula formateada.
    Si no hay fila o falla la consulta: columna **ERROR EMAIL** (misma leyenda; Gmail solo etiqueta ERROR EMAIL).
    """
    c_raw, _motivo = _cedula_por_email_cliente(db, sender_lc)
    if c_raw:
        return formatear_cedula(c_raw), True
    return PAGOS_GMAIL_ERROR_CEDULA_EMAIL, False


def run_pipeline(
    db: Session,
    existing_sync_id: Optional[int] = None,
    scan_filter: str = "all",
) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline Gmail -> Gemini -> BD (comprobante en pago_comprobante_imagen; sin subidas a Drive).
    Flujo de clasificación (etiqueta final única):
    1) Paso 1: detectar A/B desde el inicio (sin importar número de adjuntos) -> etiqueta MERCANTIL o BNC.
    2) Paso 2: si no hubo A/B, validar remitente en `clientes`; con cliente, clasificar C/D y etiquetar BINANCE o BNV.
    3) Fallback: si no aplica 1/2, usar orden TEXTO -> MASTER -> ERROR EMAIL -> MANUAL.
    Regla innegociable: solo puede quedar **una** etiqueta final por correo, y si el mensaje ya trae cualquier etiqueta de usuario se omite sin reescanear.
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (por defecto API/UI: all).
      Por defecto (**all** / **pending_identification**): inbox con imagen/PDF — leidos y no leidos (el pipeline no modifica estrellas Gmail),
      con cualquier etiqueta de usuario (incluye **ERROR EMAIL**; la consulta Gmail no excluye esa etiqueta).
      **unread** / **read**: mismo criterio base + ``is:unread`` / ``is:read`` en la búsqueda Gmail; los que entran como no leidos se marcan **leidos** al procesarlos en la corrida.
      **error_email_rescan**: listado ERROR EMAIL + media; se procesan mensajes cuya **unica** etiqueta de usuario sea **ERROR EMAIL**; si hay mas etiquetas de usuario, se omiten.
      pending_identification es alias del listado base (nombre conservado para scheduler/API).
    Regla de volumen: una imagen candidata (adjunta o embebida) = una fila = un pago, si cumple prompts y reglas.
    Orden comprobantes OK: insert sync_item + gmail_temporal -> flush -> persistir binario (con posible reuso del BLOB por SHA-256) y URL en drive_link -> commit atomico.
    Los mensajes de cada corrida se listan **todos** los que cumplen el criterio **q** (paginacion Gmail hasta agotar nextPageToken),
    se ordenan como bandeja tipica (**mas reciente primero**, mas antiguo al final) y se procesan en ese orden del primero al ultimo.
    Pasada principal de listado+proceso por ejecucion; al final, listado+proceso adicional **MANUAL+ERROR EMAIL** (redig).
    Cada mensaje que **entraba no leido** (labelIds al listar) se marca **leido** al terminar de procesarlo en esa corrida.
    Mensajes con etiquetas de usuario Gmail se omiten salvo que sean **solo** combinaciones de **MANUAL** y/o **ERROR EMAIL** (en **all** / **unread** / **read** / **pending_identification**; re-lectura A/B con cédula en imagen solo si es **exactamente** ERROR EMAIL), modo ``error_email_rescan``, o pasada redig **MANUAL+ERROR**. Fallo al listar catalogo de etiquetas: metrica ``gmail_labels_list_failed`` y no se aplica omision por etiqueta.
    No hay dedupe por contenido para saltar candidatos: cada imagen/PDF 1p se escanea y evalúa.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    logger.info("[PAGOS_GMAIL] INICIO pipeline (existing_sync_id=%s, scan_filter=%s)", existing_sync_id, scan_filter)
    creds = get_pagos_gmail_credentials()
    if not creds:
        if existing_sync_id:
            try:
                from sqlalchemy import select as sa_select
                sync_row = db.execute(sa_select(PagosGmailSync).where(PagosGmailSync.id == existing_sync_id)).scalars().first()
                if sync_row:
                    sync_row.status = "error"
                    sync_row.finished_at = _finished_at_naive_utc()
                    sync_row.error_message = "no_credentials"
                    db.commit()
            except Exception:
                pass
        logger.warning("[PAGOS_GMAIL] Sin credenciales; pipeline abortado")
        return existing_sync_id, "no_credentials"

    logger.info("[PAGOS_GMAIL] Credenciales OK; construyendo servicio Gmail")
    gmail_svc = build_gmail_service(creds)
    # Etiquetas nuevas en Gmail (UI u otra sesión) no aparecen en la caché por id(service);
    # sin refrescar, list_gmail_user_label_ids / get_existing_user_label_id pueden ignorar reglas recientes.
    invalidate_gmail_labels_list_cache(gmail_svc)
    logger.info("[PAGOS_GMAIL] Servicio Gmail construido (pipeline sin Google Drive); catálogo de etiquetas se recarga en esta corrida")

    if existing_sync_id:
        from sqlalchemy import select as sa_select
        sync = db.execute(sa_select(PagosGmailSync).where(PagosGmailSync.id == existing_sync_id)).scalars().first()
        if not sync:
            sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
            db.add(sync)
            db.commit()
            db.refresh(sync)
    else:
        sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
        db.add(sync)
        db.commit()
        db.refresh(sync)

    sync_id = sync.id
    emails_ok = 0
    files_ok = 0
    # Correos con digitalizacion 100%% y etiquetas de plantilla aplicadas + marcados leidos en Gmail.
    correos_marcados_revision = 0
    plantilla_label_cache: Dict[str, Optional[str]] = {}
    error_email_rescan = (scan_filter or "").strip().lower() == "error_email_rescan"
    # Misma corrida: varias filas Excel apuntando al mismo BLOB (mismo SHA-256) sin duplicar pago_comprobante_imagen.
    comprobante_reuse_por_sha256: dict[str, tuple[str, str]] = {}
    # IDs de gmail_temporal cuyo delete inmediato falló tras alta automática OK; se reintenta antes de cerrar cada mensaje.
    pending_gmail_temporal_delete_ids: set[int] = set()
    # Métricas para GET /pagos/gmail/status → last_run_summary (diagnóstico en toast UI).
    run_stats: dict[str, int] = {
        "gmail_messages_listed": 0,
        "messages_skipped_invalid_sender": 0,
        "messages_skipped_drive_folder": 0,
        "messages_skipped_clasificacion_etiqueta": 0,
        "messages_final_label_applied": 0,
        "messages_no_final_label": 0,
        "final_paso_1_a": 0,
        "final_paso_1_b": 0,
        "final_paso_2_c": 0,
        "final_paso_2_d": 0,
        "final_fallback_texto": 0,
        "final_fallback_master": 0,
        "final_fallback_error_email": 0,
        "final_fallback_manual": 0,
        "gmail_labels_list_failed": 0,
        "manual_error_redigitaliza_listed": 0,
        "manual_error_redigitaliza_error": "",
    }

    try:
        from app.core.config import settings as _settings_pipeline

        _gemini_model_snapshot = (
            (_settings_pipeline.GEMINI_MODEL or "").strip() or "gemini-2.5-flash"
        )

        def fetch_sorted_batch() -> list[dict]:
            raw_messages = list_messages_by_filter(gmail_svc, scan_filter)
            messages = _dedupe_messages_pagos_gmail(raw_messages)
            if len(messages) < len(raw_messages):
                logger.info(
                    "[PAGOS_GMAIL] Duplicados eliminados: %d -> %d mensajes",
                    len(raw_messages),
                    len(messages),
                )
            ordered = _sort_messages_inbox_primero_a_ultimo(messages)
            logger.info(
                "[PAGOS_GMAIL] Correos (filtro=%s): %d — listado Gmail completo (paginas hasta sin nextPageToken); "
                "orden bandeja: mas reciente primero -> mas antiguo ultimo (internalDate; si no, cabecera Date). "
                "Procesamiento: posicion 0 a N-1 sin saltos.",
                scan_filter,
                len(ordered),
            )
            if ordered:
                first = ordered[0]
                last = ordered[-1]
                logger.info(
                    "[PAGOS_GMAIL] Ventana ordenada (primero bandeja -> ultimo): id=%s internalDate_ms=%s ... "
                    "id=%s internalDate_ms=%s",
                    first.get("id"),
                    first.get("internal_date_ms"),
                    last.get("id"),
                    last.get("internal_date_ms"),
                )
            return ordered

        def process_message_batch(
            batch: list[dict],
            label: str,
            *,
            redig_manual_error_pass: bool = False,
        ) -> None:
            nonlocal emails_ok, files_ok, correos_marcados_revision
            if batch:
                logger.info(
                    "[PAGOS_GMAIL] Procesando lote %s: %d correos (imagen/PDF pipeline, formatos A/B/C/D)%s",
                    label,
                    len(batch),
                    " [redig MANUAL+ERROR EMAIL]" if redig_manual_error_pass else "",
                )
            # Etiquetas type=user: no re-escaneo, salvo solo MANUAL y/o ERROR EMAIL (subconjunto), error_email_rescan,
            # o exactamente MANUAL+ERROR en pasada redig.
            (
                _gmail_user_label_ids,
                _gmail_user_label_names,
                _labels_catalog_ok,
            ) = list_gmail_user_label_ids(gmail_svc)
            if not _labels_catalog_ok:
                run_stats["gmail_labels_list_failed"] += 1
                logger.error(
                    "[PAGOS_GMAIL] Fallo al obtener catalogo de etiquetas Gmail; "
                    "no se omite por etiquetas usuario en este lote (revisa API/cuota)."
                )
            for msg_info in batch:
                msg_id = msg_info["id"]
                _tid_raw = (msg_info.get("thread_id") or "").strip()
                gmail_thread_id: Optional[str] = _tid_raw[:100] if _tid_raw else None

                def _pipeline_evt(
                    motivo: str,
                    *,
                    sha256_hex: Optional[str] = None,
                    filename: Optional[str] = None,
                    detalle: Optional[str] = None,
                ) -> None:
                    registrar_pagos_gmail_pipeline_evento(
                        db,
                        sync_id=sync_id,
                        gmail_message_id=msg_id,
                        gmail_thread_id=gmail_thread_id,
                        motivo=motivo,
                        sha256_hex=sha256_hex,
                        filename=filename,
                        detalle=detalle,
                    )

                label_ids_snapshot = list(msg_info.get("label_ids") or [])
                was_unread = "UNREAD" in label_ids_snapshot
                msg_lids_set = frozenset(label_ids_snapshot)
                _user_on_msg = msg_lids_set & _gmail_user_label_ids
                k_err_shared = PAGOS_GMAIL_LABEL_ERROR_EMAIL
                if k_err_shared not in plantilla_label_cache:
                    plantilla_label_cache[k_err_shared] = ensure_user_label_id(
                        gmail_svc, k_err_shared
                    )
                mid_err_shared = plantilla_label_cache.get(k_err_shared)
                if _labels_catalog_ok and _user_on_msg:
                    _skip_por_etiquetas_usuario = True
                    _hit_names = sorted(
                        _gmail_user_label_names.get(lid, lid) for lid in _user_on_msg
                    )
                    run_stats["messages_skipped_clasificacion_etiqueta"] += 1
                    logger.info(
                        "[PAGOS_GMAIL]   Omitido: mensaje con etiqueta(s) de usuario Gmail [%s] — "
                        "sin escanear de nuevo ni filas Excel/BD (msg=%s)",
                        ", ".join(_hit_names),
                        msg_id,
                    )
                    _pipeline_evt(
                        EVT_OMISION_ETIQUETA_USUARIO,
                        detalle=", ".join(_hit_names)[:8000],
                    )
                    if was_unread:
                        mark_as_read(gmail_svc, msg_id)
                    continue
                payload = msg_info["payload"]
                headers = msg_info["headers"]
                from_h = headers.get("from") or headers.get("From") or ""
                sender = extract_sender_email(from_h)
                sender_lc = (sender or "").strip().lower()
                if (
                    not sender_lc
                    or sender_lc == "desconocido"
                    or "@" not in sender_lc
                ):
                    logger.info(
                        "[PAGOS_GMAIL]   Omitido: remitente (De) sin email valido (%s) msg=%s",
                        sender_lc[:72] if sender_lc else "(vacio)",
                        msg_id,
                    )
                    _pipeline_evt(EVT_REMITENTE_INVALIDO, detalle=(sender_lc[:200] or "(vacio)"))
                    run_stats["messages_skipped_invalid_sender"] += 1
                    if was_unread:
                        mark_as_read(gmail_svc, msg_id)
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: LEIDO tras escaneo (no leido al listar; remitente omitido)"
                        )
                    continue
                remitente_solo_master = sender_lc == PAGOS_GMAIL_SENDER_MASTER
                _ced_lookup, _ = _cedula_por_email_cliente(db, sender_lc)
                remitente_en_clientes = _ced_lookup is not None
                subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
                msg_date = get_message_date(headers)
                sheet_name = get_sheet_name_for_date(msg_date)

                # Mercantil/BNC (A/B): cédula desde imagen en re-escaneo, redig MANUAL+ERROR, o inbox con **solo** ERROR EMAIL.
                solo_error_email_inbox = (
                    not error_email_rescan
                    and not redig_manual_error_pass
                    and _labels_catalog_ok
                    and bool(mid_err_shared)
                    and _user_on_msg == frozenset({mid_err_shared})
                )
                modo_ab_cedula_desde_imagen = (
                    error_email_rescan or redig_manual_error_pass or solo_error_email_inbox
                )
                # Sin fila en clientes (correo De no en BD): no inventar C/D/NR; solo intentar Mercantil/BNC (A/B) con cédula en imagen.
                plan_b_mercantil_bnc_fuera_bd = (
                    not remitente_en_clientes
                    and not remitente_solo_master
                    and not error_email_rescan
                    and not redig_manual_error_pass
                    and not solo_error_email_inbox
                )
                usar_extraccion_cedula_imagen_ab = (
                    modo_ab_cedula_desde_imagen or plan_b_mercantil_bnc_fuera_bd
                )
                if modo_ab_cedula_desde_imagen:
                    _modo_nom = (
                        "error_email_rescan"
                        if error_email_rescan
                        else (
                            "redig_manual_error"
                            if redig_manual_error_pass
                            else (
                                "solo_error_email_inbox"
                                if solo_error_email_inbox
                                else "?"
                            )
                        )
                    )
                    logger.info(
                        "[PAGOS_GMAIL]   Modo cedula imagen A/B (%s); msg=%s",
                        _modo_nom,
                        msg_id,
                    )
                elif plan_b_mercantil_bnc_fuera_bd:
                    logger.info(
                        "[PAGOS_GMAIL]   Plan B (De no en clientes): solo Mercantil/BNC si Gemini aplica A o B "
                        "(cédula desde imagen); si no, ERROR EMAIL; msg=%s",
                        msg_id,
                    )

                logger.info(
                    "[PAGOS_GMAIL] -- Correo %d (%s) id=%s | de=%s | asunto=%s",
                    emails_ok + 1,
                    label,
                    msg_id,
                    sender[:40],
                    subject[:50],
                )

                full_payload = get_message_full_payload(gmail_svc, msg_id)
                if not full_payload and payload.get("parts"):
                    full_payload = payload

                attachments = get_pagos_gmail_image_pdf_files_for_pipeline(
                    gmail_svc, msg_id, full_payload or {}
                )
                candidatos, multipage_pdf_omitidos = expand_pipeline_pdf_tuples(attachments)

                logger.info(
                    "[PAGOS_GMAIL]   candidatos imagen/PDF (adjunto + embebido + reenvio; PDF 2+ pag omitidos=%d): %d - %s",
                    multipage_pdf_omitidos,
                    len(candidatos),
                    ", ".join(f"{f}({len(c)}B,{o})" for f, c, _, o in candidatos)
                    if candidatos
                    else "ninguno",
                )

                had_complete_digitalization = False
                any_incomplete_or_skipped = False
                any_cedula_lookup_failed = False
                # True solo si un adjunto se descarta por formato/parse (no por cedula del remitente).
                any_skipped_not_plantilla_o_campos = False
                label_ids_for_message: list[str] = []
                # Formatos A/B/C/D/NR digitalizados OK (comprobante en BD) en este mensaje (para detectar mezcla -> MANUAL).
                bank_fmts_digitized: list[str] = []
                if not candidatos:
                    any_incomplete_or_skipped = True
                    if multipage_pdf_omitidos > 0:
                        _pipeline_evt(
                            EVT_SOLO_PDF_MULTIPAGINA,
                            detalle=f"omitidos_pdf_2p={multipage_pdf_omitidos}",
                        )
                    else:
                        _pipeline_evt(EVT_SIN_ADJUNTOS_DIGITABLES)
                if (
                    not remitente_en_clientes
                    and candidatos
                    and not solo_error_email_inbox
                    and not plan_b_mercantil_bnc_fuera_bd
                ):
                    logger.info(
                        "[PAGOS_GMAIL]   Remitente no en clientes.email/email_secundario (o fallo al consultar): "
                        "sin Gemini ni filas Excel/BD; Gmail solo ERROR EMAIL (msg_id=%s).",
                        msg_id,
                    )
                    _pipeline_evt(
                        EVT_REMITENTE_NO_CLIENTE_CON_MEDIA,
                        detalle=f"de={sender_lc[:120]} adjuntos={len(candidatos)}",
                    )

                def _campos_completos(fecha: str, cedula: str, monto: str, ref: str) -> bool:
                    def ok(val: str) -> bool:
                        s = (val or "").strip()
                        return bool(s) and s.upper() != PAGOS_NA

                    return ok(fecha) and ok(cedula) and ok(monto) and ok(ref)

                def _campos_completos_nr(cedula: str, monto: str) -> bool:
                    """Fila NR: monto literal NR; cédula columna debe existir (cliente o ERROR EMAIL)."""
                    s_m = (monto or "").strip().upper()
                    if s_m != "NR":
                        return False
                    s_c = (cedula or "").strip()
                    return bool(s_c) and s_c.upper() != PAGOS_NA

                def _insert_rows_sin_drive(
                    correo: str,
                    fecha: str,
                    cedula: str,
                    monto: str,
                    referencia: str,
                    banco: str,
                ) -> Optional[tuple[PagosGmailSyncItem, GmailTemporal]]:
                    try:
                        si = PagosGmailSyncItem(
                            sync_id=sync_id,
                            correo_origen=correo,
                            asunto=subject,
                            banco=banco,
                            fecha_pago=fecha,
                            cedula=cedula,
                            monto=monto,
                            numero_referencia=referencia,
                            drive_file_id=None,
                            drive_link=None,
                            drive_email_link=None,
                            sheet_name=sheet_name,
                            gmail_message_id=(msg_id or "")[:100] or None,
                            gmail_thread_id=gmail_thread_id,
                        )
                        gt = GmailTemporal(
                            correo_origen=correo,
                            asunto=subject,
                            banco=banco,
                            fecha_pago=fecha,
                            cedula=cedula,
                            monto=monto,
                            numero_referencia=referencia,
                            drive_file_id=None,
                            drive_link=None,
                            drive_email_link=None,
                            sheet_name=sheet_name,
                            gmail_message_id=(msg_id or "")[:100] or None,
                            gmail_thread_id=gmail_thread_id,
                        )
                        db.add(si)
                        db.add(gt)
                        return (si, gt)
                    except Exception as db_err:
                        logger.warning("[PAGOS_GMAIL] Error preparando filas BD: %s", db_err)
                        return None

                def _v(x: Optional[str]) -> str:
                    v = (x or "").strip()
                    return v if v and v.upper() != "NA" else ""

                pending: list[dict] = []
                committed_comprobante_rows = False
                candidatos_loop = (
                    candidatos
                    if (
                        remitente_en_clientes
                        or redig_manual_error_pass
                        or solo_error_email_inbox
                        or error_email_rescan
                        or plan_b_mercantil_bnc_fuera_bd
                    )
                    else []
                )
                for filename, content, mime_type, origen_binario in candidatos_loop:
                    try:
                        body_bin = (
                            content
                            if isinstance(content, (bytes, bytearray))
                            else bytes(content)
                        )
                        file_digest = hashlib.sha256(body_bin).hexdigest()

                        fmt, data = classify_and_extract_pagos_gmail_attachment(
                            content,
                            filename,
                            remitente_correo_header=from_h,
                            origen_binario=origen_binario,
                            modo_error_email_ab=usar_extraccion_cedula_imagen_ab,
                        )

                        if redig_manual_error_pass and fmt not in ("A", "B"):
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.info(
                                "[PAGOS_GMAIL] redig MANUAL+ERROR: Gemini no clasifica Mercantil/BNC (formato=%r) — "
                                "sin digitalizar %s",
                                fmt,
                                filename,
                            )
                            _pipeline_evt(
                                EVT_NO_PLANTILLA_GEMINI,
                                filename=filename,
                                detalle=(f"redig_solo_ab:{fmt!s}")[:500],
                            )
                            continue

                        if fmt not in PAGOS_GMAIL_FORMATOS_PLANTILLA:
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.warning(
                                "[PAGOS_GMAIL]   No es plantilla A/B/C/D - no BD: %s",
                                filename,
                            )
                            _pipeline_evt(
                                EVT_NO_PLANTILLA_GEMINI,
                                filename=filename,
                                detalle=(fmt or "?")[:500],
                            )
                            continue

                        if (
                            plan_b_mercantil_bnc_fuera_bd
                            and fmt in PAGOS_GMAIL_FORMATOS_PLANTILLA
                            and fmt not in ("A", "B")
                        ):
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.info(
                                "[PAGOS_GMAIL]   Plan B: formato %s no Mercantil/BNC aplicable (solo A/B) — %s",
                                fmt,
                                filename,
                            )
                            _pipeline_evt(
                                EVT_NO_PLANTILLA_GEMINI,
                                filename=filename,
                                detalle=(f"plan_b_solo_ab:{fmt!s}")[:500],
                            )
                            continue

                        if fmt == "C":
                            f = normalizar_fecha_pago(msg_date.strftime("%d/%m/%Y"))
                            m = _v(data.get("monto"))
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            c, c_ok = _cedula_columna_desde_remitente(db, sender_lc)
                            if not c_ok:
                                any_incomplete_or_skipped = True
                                any_cedula_lookup_failed = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   BINANCE (C): columna Cedula=%s — De=%s archivo=%s",
                                    c,
                                    sender_lc[:72],
                                    filename,
                                )
                        elif fmt == "NR":
                            f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                            m = "NR"
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            c, c_ok = _cedula_columna_desde_remitente(db, sender_lc)
                            if not c_ok:
                                any_incomplete_or_skipped = True
                                any_cedula_lookup_failed = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   NR (no RapiCredit): columna Cedula=%s — De=%s archivo=%s",
                                    c,
                                    sender_lc[:72],
                                    filename,
                                )
                        elif usar_extraccion_cedula_imagen_ab and fmt in ("A", "B"):
                            f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                            m = _v(data.get("monto"))
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            c = _cedula_desde_imagen_rescan_error_email(data.get("cedula"))
                            c_ok = True
                            _log_ab = (
                                "Plan B (sin De en clientes)"
                                if plan_b_mercantil_bnc_fuera_bd
                                else "Re-scan ERROR EMAIL"
                            )
                            logger.info(
                                "[PAGOS_GMAIL]   %s (%s): columna Cedula desde imagen=%s archivo=%s",
                                _log_ab,
                                fmt,
                                c[:24] if c else "",
                                filename,
                            )
                        else:
                            f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                            m = _v(data.get("monto"))
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            c, c_ok = _cedula_columna_desde_remitente(db, sender_lc)
                            if not c_ok:
                                any_incomplete_or_skipped = True
                                any_cedula_lookup_failed = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   MERCANTIL/BNC/BNV (%s): columna Cedula=%s — De=%s archivo=%s",
                                    fmt,
                                    c,
                                    sender_lc[:72],
                                    filename,
                                )
                        # Sin cédula de cliente no hay fila Excel/BD (la literal ERROR EMAIL no se exporta).
                        if not c_ok:
                            any_incomplete_or_skipped = True
                            any_cedula_lookup_failed = True
                            continue
                        if fmt == "NR":
                            if not _campos_completos_nr(c, m):
                                any_incomplete_or_skipped = True
                                any_skipped_not_plantilla_o_campos = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   Formato NR pero fila incompleta (monto!=NR o cedula vacia) - no BD: %s",
                                    filename,
                                )
                                _pipeline_evt(
                                    EVT_CAMPOS_INCOMPLETOS_PLANTILLA,
                                    filename=filename,
                                    detalle="NR",
                                )
                                continue
                        elif not _campos_completos(f, c, m, r):
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.warning(
                                "[PAGOS_GMAIL]   Plantilla %s pero columnas incompletas - no BD: %s",
                                fmt,
                                filename,
                            )
                            _pipeline_evt(
                                EVT_CAMPOS_INCOMPLETOS_PLANTILLA,
                                filename=filename,
                                detalle=(fmt or "?")[:80],
                            )
                            continue

                        banco_excel = resolve_banco_para_excel_pagos_gmail(
                            fmt,
                            (data.get("banco") or "").strip(),
                            default_a=PAGOS_GMAIL_BANCO_IMAGEN_1,
                            default_b=PAGOS_GMAIL_BANCO_IMAGEN_2,
                            default_c=PAGOS_GMAIL_BANCO_IMAGEN_3,
                            default_d=PAGOS_GMAIL_BANCO_IMAGEN_4,
                        )
                        # Re-escaneo A/B (solo_error / redig / error_email_rescan): cédula ilegible -> literal "ERROR".
                        # _campos_completos acepta "ERROR" como texto no vacío; sin esto, fully_digitized_email=True
                        # y se quita ERROR EMAIL o se añade PROCESADO en redig aunque la cédula no sea válida.
                        if (
                            usar_extraccion_cedula_imagen_ab
                            and fmt in ("A", "B")
                            and c == PAGOS_GMAIL_ERROR_CEDULA_IMAGEN
                        ):
                            any_incomplete_or_skipped = True
                        pending.append(
                            {
                                "fmt": fmt,
                                "f": f,
                                "c": c,
                                "m": m,
                                "r": r,
                                "monto_operacion": _v(data.get("monto_operacion")),
                                "banco_excel": banco_excel,
                                "filename": filename,
                                "content": content,
                                "mime_type": mime_type,
                                "sha256": file_digest,
                            }
                        )
                    except Exception as e:
                        logger.warning("[PAGOS_GMAIL]   Error procesando %s: %s", filename, e)
                        _pipeline_evt(
                            EVT_ERROR_PROCESAR_ADJUNTO,
                            filename=filename,
                            detalle=str(e)[:800],
                        )
                        any_incomplete_or_skipped = True
                        any_skipped_not_plantilla_o_campos = True

                if redig_manual_error_pass and candidatos and not pending:
                    logger.info(
                        "[PAGOS_GMAIL] redig MANUAL+ERROR: sin fila Mercantil/BNC valida tras Gemini "
                        "(o dedupe/campos; candidatos=%d) msg=%s",
                        len(candidatos),
                        msg_id,
                    )
                    if was_unread:
                        mark_as_read(gmail_svc, msg_id)
                    emails_ok += 1
                    sync.emails_processed = emails_ok
                    sync.files_processed = files_ok
                    db.commit()
                    continue

                rows_pairs: list[tuple[PagosGmailSyncItem, GmailTemporal, dict]] = []
                if pending:
                    for p in pending:
                        inserted = _insert_rows_sin_drive(
                            sender,
                            p["f"],
                            p["c"],
                            p["m"],
                            p["r"],
                            p["banco_excel"],
                        )
                        if inserted is None:
                            db.rollback()
                            any_incomplete_or_skipped = True
                            rows_pairs = []
                            break
                        rows_pairs.append((inserted[0], inserted[1], p))

                    if rows_pairs:
                        try:
                            db.flush()
                        except Exception as flush_err:
                            logger.warning(
                                "[PAGOS_GMAIL] Error flush filas sync/temporal antes de comprobante: %s",
                                flush_err,
                            )
                            db.rollback()
                            any_incomplete_or_skipped = True
                            rows_pairs = []
                        else:
                            _label_ids_len_before_comprobante = len(label_ids_for_message)
                            comprobante_resueltos: list[tuple[str, str, dict, PagosGmailSyncItem]] = []
                            persist_ok = True
                            for si, gt, p in rows_pairs:
                                sh_raw = p.get("sha256")
                                sh_key: Optional[str] = None
                                if isinstance(sh_raw, str) and len(sh_raw.strip()) == 64:
                                    cand = sh_raw.strip().lower()
                                    if all(c in "0123456789abcdef" for c in cand):
                                        sh_key = cand
                                persisted = persistir_comprobante_gmail_en_bd(
                                    db,
                                    p["content"],
                                    p["mime_type"],
                                    sha256_hex=sh_key,
                                    reuse_por_sha256=comprobante_reuse_por_sha256,
                                )
                                if not persisted:
                                    persist_ok = False
                                    logger.warning(
                                        "[PAGOS_GMAIL]   No se pudo guardar comprobante en BD — "
                                        "rollback de filas de este correo: %s",
                                        p["filename"],
                                    )
                                    break
                                _uid, link_url = persisted
                                comprobante_resueltos.append(
                                    (_uid, link_url or "", p, si)
                                )
                                logger.info(
                                    "[PAGOS_GMAIL]   Comprobante en sesion OK: %s -> %s",
                                    p["filename"],
                                    (link_url or "")[:72],
                                )
                                si.drive_file_id = None
                                si.drive_link = link_url or None
                                si.drive_email_link = None
                                gt.drive_file_id = None
                                gt.drive_link = link_url or None
                                gt.drive_email_link = None
                                fmt = p["fmt"]
                                id_a, id_b, id_c, id_d = get_or_create_pagos_gmail_plantilla_label_ids(
                                    gmail_svc, plantilla_label_cache
                                )
                                if fmt == "A":
                                    label_id = id_a
                                    etiqueta_nombre = PAGOS_GMAIL_LABEL_IMAGEN_1
                                elif fmt == "B":
                                    label_id = id_b
                                    etiqueta_nombre = PAGOS_GMAIL_LABEL_IMAGEN_2
                                elif fmt == "D":
                                    label_id = id_d
                                    etiqueta_nombre = PAGOS_GMAIL_LABEL_IMAGEN_4
                                elif fmt == "C":
                                    label_id = id_c
                                    etiqueta_nombre = PAGOS_GMAIL_LABEL_IMAGEN_3
                                elif fmt == "NR":
                                    label_id = None
                                    etiqueta_nombre = "NR"
                                else:
                                    label_id = None
                                    etiqueta_nombre = fmt or "?"
                                if (
                                    label_id
                                    and not remitente_solo_master
                                    and (
                                        remitente_en_clientes
                                        or redig_manual_error_pass
                                        or solo_error_email_inbox
                                        or plan_b_mercantil_bnc_fuera_bd
                                    )
                                ):
                                    label_ids_for_message.append(label_id)
                                logger.info(
                                    "[PAGOS_GMAIL]   Digitalizado OK (%s); etiquetas plantilla solo si 100%% candidatos: %s",
                                    etiqueta_nombre,
                                    p["filename"],
                                )

                            if not persist_ok:
                                db.rollback()
                                del label_ids_for_message[_label_ids_len_before_comprobante:]
                                any_incomplete_or_skipped = True
                            else:
                                try:
                                    db.commit()
                                    committed_comprobante_rows = True
                                    logger.info(
                                        "[PAGOS_GMAIL]   Commit BD: %d fila(s) sync/temporal + comprobante enlazado",
                                        len(rows_pairs),
                                    )
                                    for uid, link_url, p, si in comprobante_resueltos:
                                        sh_raw = p.get("sha256")
                                        if isinstance(sh_raw, str) and len(sh_raw.strip()) == 64:
                                            k = sh_raw.strip().lower()
                                            if all(c in "0123456789abcdef" for c in k):
                                                comprobante_reuse_por_sha256[k] = (uid, link_url)
                                        files_ok += 1
                                        had_complete_digitalization = True
                                        fmt_row = p["fmt"]
                                        if fmt_row in ("A", "B", "C", "D", "NR"):
                                            bank_fmts_digitized.append(fmt_row)
                                        if es_plantilla_banco_abcd(fmt_row):
                                            try:
                                                dup_doc = (
                                                    item_sync_abcd_candidato_revision_duplicado(
                                                        fmt=fmt_row,
                                                        banco_excel=p.get(
                                                            "banco_excel"
                                                        ),
                                                        referencia=p.get("r"),
                                                        db=db,
                                                    )
                                                )
                                                logger.info(
                                                    "[PAGOS_GMAIL] [REGLA_ABCD] Plantilla %s archivo=%s | %s | "
                                                    "serial_ya_en_pagos_o_pagos_con_errores=%s",
                                                    fmt_row,
                                                    p.get("filename"),
                                                    resumen_log_linea_plantilla_abcd(),
                                                    dup_doc,
                                                )
                                                sid = getattr(si, "id", None)
                                                ssync = getattr(si, "sync_id", None)
                                                if dup_doc:
                                                    registrar_traza_gmail_abcd_cuotas_evento(
                                                        db,
                                                        sync_id=ssync,
                                                        sync_item_id=sid,
                                                        plantilla_fmt=fmt_row,
                                                        cedula=p.get("c"),
                                                        numero_referencia=p.get("r"),
                                                        banco_excel=p.get("banco_excel"),
                                                        archivo_adjunto=p.get("filename"),
                                                        comprobante_imagen_id=uid,
                                                        duplicado_documento=True,
                                                        etapa_final="OMITIDO_DUPLICADO",
                                                    )
                                                else:
                                                    res_abcd = (
                                                        crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
                                                            db,
                                                            cedula_columna=p.get("c")
                                                            or "",
                                                            fecha_pago_str=p.get("f")
                                                            or "",
                                                            monto_str=p.get("m") or "",
                                                            numero_referencia=p.get("r")
                                                            or "",
                                                            institucion_bancaria=p.get(
                                                                "banco_excel"
                                                            ),
                                                            link_comprobante=link_url,
                                                            fmt=fmt_row,
                                                            filename=p.get("filename"),
                                                            sync_id=ssync,
                                                            sync_item_id=sid,
                                                            comprobante_imagen_id=uid,
                                                        )
                                                    )
                                                    if res_abcd.get("ok"):
                                                        logger.info(
                                                            "[PAGOS_GMAIL] [ABCD_PAGO] Alta pagos+cuotas OK: %s",
                                                            res_abcd,
                                                        )
                                                        if (
                                                            str(res_abcd.get("etapa_final") or "")
                                                            == "CUOTAS_OK"
                                                        ):
                                                            _gt_del_id = None
                                                            for _sii, _gt, _pp in rows_pairs:
                                                                if (
                                                                    getattr(_sii, "id", None)
                                                                    is not None
                                                                    and getattr(si, "id", None)
                                                                    is not None
                                                                    and int(_sii.id) == int(si.id)
                                                                ):
                                                                    _gt_del_id = getattr(
                                                                        _gt, "id", None
                                                                    )
                                                                    break
                                                            if _gt_del_id is not None:
                                                                try:
                                                                    db.execute(
                                                                        delete(GmailTemporal).where(
                                                                            GmailTemporal.id
                                                                            == int(_gt_del_id)
                                                                        )
                                                                    )
                                                                    db.commit()
                                                                    logger.info(
                                                                        "[PAGOS_GMAIL] [ABCD_PAGO] "
                                                                        "gmail_temporal id=%s omitida de Excel "
                                                                        "(CUOTAS_OK, pago en BD)",
                                                                        _gt_del_id,
                                                                    )
                                                                except Exception as _gt_exc:
                                                                    logger.warning(
                                                                        "[PAGOS_GMAIL] [ABCD_PAGO] "
                                                                        "No se pudo eliminar gmail_temporal id=%s: %s",
                                                                        _gt_del_id,
                                                                        _gt_exc,
                                                                    )
                                                                    try:
                                                                        pending_gmail_temporal_delete_ids.add(
                                                                            int(_gt_del_id)
                                                                        )
                                                                    except Exception:
                                                                        pass
                                                                    try:
                                                                        db.rollback()
                                                                    except Exception:
                                                                        pass
                                                        else:
                                                            logger.warning(
                                                                "[PAGOS_GMAIL] [ABCD_PAGO] pago_id=%s sin aplicación a cuotas "
                                                                "(etapa=%s): permanece en revisión manual",
                                                                res_abcd.get("pago_id"),
                                                                res_abcd.get("etapa_final"),
                                                            )
                                                    else:
                                                        logger.warning(
                                                            "[PAGOS_GMAIL] [ABCD_PAGO] Sin alta automatica: "
                                                            "motivo=%s detalle=%s",
                                                            res_abcd.get("motivo"),
                                                            (res_abcd.get("detalle") or "")[:160],
                                                        )
                                                        registrar_traza_gmail_abcd_cuotas_evento(
                                                            db,
                                                            sync_id=ssync,
                                                            sync_item_id=sid,
                                                            plantilla_fmt=fmt_row,
                                                            cedula=p.get("c"),
                                                            numero_referencia=p.get("r"),
                                                            banco_excel=p.get("banco_excel"),
                                                            archivo_adjunto=p.get("filename"),
                                                            comprobante_imagen_id=uid,
                                                            duplicado_documento=False,
                                                            etapa_final="OMITIDO_NEGOCIO",
                                                            motivo=str(
                                                                res_abcd.get("motivo") or ""
                                                            )[:80]
                                                            or None,
                                                            detalle=str(
                                                                res_abcd.get("detalle") or ""
                                                            )[:4000]
                                                            or None,
                                                        )
                                            except Exception as dup_exc:
                                                logger.warning(
                                                    "[PAGOS_GMAIL] [REGLA_ABCD] Evaluacion duplicado documento: %s",
                                                    dup_exc,
                                                )
                                                try:
                                                    registrar_traza_gmail_abcd_cuotas_evento(
                                                        db,
                                                        sync_id=getattr(
                                                            si, "sync_id", None
                                                        ),
                                                        sync_item_id=getattr(si, "id", None),
                                                        plantilla_fmt=fmt_row,
                                                        cedula=p.get("c"),
                                                        numero_referencia=p.get("r"),
                                                        banco_excel=p.get("banco_excel"),
                                                        archivo_adjunto=p.get("filename"),
                                                        comprobante_imagen_id=uid,
                                                        duplicado_documento=False,
                                                        etapa_final="ERROR_PIPELINE",
                                                        motivo="excepcion",
                                                        detalle=str(dup_exc)[:4000],
                                                    )
                                                except Exception:
                                                    pass
                                        elif fmt_row == "NR":
                                            try:
                                                m_op = (p.get("monto_operacion") or "").strip()
                                                if (
                                                    not m_op
                                                    or m_op.upper() == PAGOS_NA
                                                    or m_op.upper() == "NR"
                                                ):
                                                    registrar_traza_gmail_abcd_cuotas_evento(
                                                        db,
                                                        sync_id=getattr(
                                                            si, "sync_id", None
                                                        ),
                                                        sync_item_id=getattr(si, "id", None),
                                                        plantilla_fmt="NR",
                                                        cedula=p.get("c"),
                                                        numero_referencia=p.get("r"),
                                                        banco_excel=p.get("banco_excel"),
                                                        archivo_adjunto=p.get("filename"),
                                                        comprobante_imagen_id=uid,
                                                        duplicado_documento=False,
                                                        etapa_final="OMITIDO_SIN_MONTO_OPERACION",
                                                        motivo="monto_operacion",
                                                        detalle="NA o vacio",
                                                    )
                                                else:
                                                    dup_nr = (
                                                        item_sync_nr_candidato_revision_duplicado(
                                                            referencia=p.get("r"),
                                                            db=db,
                                                        )
                                                    )
                                                    sid = getattr(si, "id", None)
                                                    ssync = getattr(si, "sync_id", None)
                                                    if dup_nr:
                                                        registrar_traza_gmail_abcd_cuotas_evento(
                                                            db,
                                                            sync_id=ssync,
                                                            sync_item_id=sid,
                                                            plantilla_fmt="NR",
                                                            cedula=p.get("c"),
                                                            numero_referencia=p.get("r"),
                                                            banco_excel=p.get("banco_excel"),
                                                            archivo_adjunto=p.get("filename"),
                                                            comprobante_imagen_id=uid,
                                                            duplicado_documento=True,
                                                            etapa_final="OMITIDO_DUPLICADO",
                                                        )
                                                    else:
                                                        res_nr = (
                                                            crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr(
                                                                db,
                                                                cedula_columna=p.get("c")
                                                                or "",
                                                                fecha_pago_str=p.get("f")
                                                                or "",
                                                                monto_operacion_str=m_op,
                                                                numero_referencia=p.get("r")
                                                                or "",
                                                                institucion_bancaria=p.get(
                                                                    "banco_excel"
                                                                ),
                                                                link_comprobante=link_url,
                                                                filename=p.get("filename"),
                                                                sync_id=ssync,
                                                                sync_item_id=sid,
                                                                comprobante_imagen_id=uid,
                                                            )
                                                        )
                                                        if res_nr.get("ok"):
                                                            logger.info(
                                                                "[PAGOS_GMAIL] [NR_PAGO] Alta pagos+cuotas OK: %s",
                                                                res_nr,
                                                            )
                                                            if (
                                                                str(res_nr.get("etapa_final") or "")
                                                                == "CUOTAS_OK"
                                                            ):
                                                                _gt_del_id = None
                                                                for _sii, _gt, _pp in rows_pairs:
                                                                    if (
                                                                        getattr(_sii, "id", None)
                                                                        is not None
                                                                        and getattr(si, "id", None)
                                                                        is not None
                                                                        and int(_sii.id)
                                                                        == int(si.id)
                                                                    ):
                                                                        _gt_del_id = getattr(
                                                                            _gt, "id", None
                                                                        )
                                                                        break
                                                                if _gt_del_id is not None:
                                                                    try:
                                                                        db.execute(
                                                                            delete(
                                                                                GmailTemporal
                                                                            ).where(
                                                                                GmailTemporal.id
                                                                                == int(_gt_del_id)
                                                                            )
                                                                        )
                                                                        db.commit()
                                                                        logger.info(
                                                                            "[PAGOS_GMAIL] [NR_PAGO] "
                                                                            "gmail_temporal id=%s omitida de Excel (CUOTAS_OK)",
                                                                            _gt_del_id,
                                                                        )
                                                                    except Exception as _gt_exc:
                                                                        logger.warning(
                                                                            "[PAGOS_GMAIL] [NR_PAGO] "
                                                                            "No se pudo eliminar gmail_temporal id=%s: %s",
                                                                            _gt_del_id,
                                                                            _gt_exc,
                                                                        )
                                                                        try:
                                                                            pending_gmail_temporal_delete_ids.add(
                                                                                int(_gt_del_id)
                                                                            )
                                                                        except Exception:
                                                                            pass
                                                                        try:
                                                                            db.rollback()
                                                                        except Exception:
                                                                            pass
                                                            else:
                                                                logger.warning(
                                                                    "[PAGOS_GMAIL] [NR_PAGO] pago_id=%s sin aplicación a cuotas "
                                                                    "(etapa=%s): permanece en revisión manual",
                                                                    res_nr.get("pago_id"),
                                                                    res_nr.get("etapa_final"),
                                                                )
                                                        else:
                                                            logger.warning(
                                                                "[PAGOS_GMAIL] [NR_PAGO] Sin alta automatica: "
                                                                "motivo=%s detalle=%s",
                                                                res_nr.get("motivo"),
                                                                (res_nr.get("detalle") or "")[:160],
                                                            )
                                                            registrar_traza_gmail_abcd_cuotas_evento(
                                                                db,
                                                                sync_id=ssync,
                                                                sync_item_id=sid,
                                                                plantilla_fmt="NR",
                                                                cedula=p.get("c"),
                                                                numero_referencia=p.get("r"),
                                                                banco_excel=p.get("banco_excel"),
                                                                archivo_adjunto=p.get("filename"),
                                                                comprobante_imagen_id=uid,
                                                                duplicado_documento=False,
                                                                etapa_final="OMITIDO_NEGOCIO",
                                                                motivo=str(
                                                                    res_nr.get("motivo") or ""
                                                                )[:80]
                                                                or None,
                                                                detalle=str(
                                                                    res_nr.get("detalle") or ""
                                                                )[:4000]
                                                                or None,
                                                            )
                                            except Exception as nr_exc:
                                                logger.warning(
                                                    "[PAGOS_GMAIL] [REGLA_NR] %s",
                                                    nr_exc,
                                                )
                                                try:
                                                    registrar_traza_gmail_abcd_cuotas_evento(
                                                        db,
                                                        sync_id=getattr(
                                                            si, "sync_id", None
                                                        ),
                                                        sync_item_id=getattr(si, "id", None),
                                                        plantilla_fmt="NR",
                                                        cedula=p.get("c"),
                                                        numero_referencia=p.get("r"),
                                                        banco_excel=p.get("banco_excel"),
                                                        archivo_adjunto=p.get("filename"),
                                                        comprobante_imagen_id=uid,
                                                        duplicado_documento=False,
                                                        etapa_final="ERROR_PIPELINE",
                                                        motivo="excepcion",
                                                        detalle=str(nr_exc)[:4000],
                                                    )
                                                except Exception:
                                                    pass
                                except Exception as upd_err:
                                    logger.warning(
                                        "[PAGOS_GMAIL] Error commit filas + comprobante en BD: %s",
                                        upd_err,
                                    )
                                    db.rollback()
                                    del label_ids_for_message[_label_ids_len_before_comprobante:]
                                    any_incomplete_or_skipped = True

                n_att = len(candidatos)
                if (
                    n_att > 1
                    and any_incomplete_or_skipped
                    and had_complete_digitalization
                ):
                    if any_skipped_not_plantilla_o_campos and any_cedula_lookup_failed:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; mezcla: uno o mas no son plantilla A/B/C/D "
                            "o datos incompletos, y ademas remitente sin cedula en clientes (ERROR EMAIL). "
                            "Sin etiquetas plantilla ni leido automatico (100%% en todos + remitente valido).",
                            n_att,
                        )
                    elif any_cedula_lookup_failed:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; comprobantes reconocidos y guardados en BD pero "
                            "remitente sin match en clientes (columna Cedula ERROR EMAIL). "
                            "En Gmail solo ERROR EMAIL (sin MERCANTIL/BNC/BINANCE/BNV).",
                            n_att,
                        )
                    elif any_skipped_not_plantilla_o_campos:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; uno o mas no son plantilla A/B/C/D valida "
                            "o fallaron -> sin etiquetas plantilla ni leido (se exige 100%% OK en todos). "
                            "Si fallo el guardado del comprobante, las filas de ese correo se revierten (sin huerfanas).",
                            n_att,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; incompleto por commit/guardado comprobante u otro fallo "
                            "-> sin etiquetas plantilla ni leido (100%% en todos).",
                            n_att,
                        )

                fully_digitized_email = (
                    len(candidatos) > 0
                    and not any_incomplete_or_skipped
                    and had_complete_digitalization
                )
                tipos_digitados_distintos = {
                    f for f in bank_fmts_digitized if f in ("A", "B", "C", "D", "NR")
                }

                final_label_name: Optional[str] = None
                final_label_reason = "none"
                label_prioridad_paso_1 = next(
                    (f for f in bank_fmts_digitized if f in ("A", "B")),
                    None,
                )
                if label_prioridad_paso_1:
                    final_label_name = (
                        PAGOS_GMAIL_LABEL_IMAGEN_1
                        if label_prioridad_paso_1 == "A"
                        else PAGOS_GMAIL_LABEL_IMAGEN_2
                    )
                    final_label_reason = f"paso_1_{label_prioridad_paso_1.lower()}"
                elif remitente_en_clientes:
                    label_prioridad_paso_2 = next(
                        (f for f in bank_fmts_digitized if f in ("C", "D")),
                        None,
                    )
                    if label_prioridad_paso_2 == "C":
                        final_label_name = PAGOS_GMAIL_LABEL_IMAGEN_3
                        final_label_reason = "paso_2_c"
                    elif label_prioridad_paso_2 == "D":
                        final_label_name = PAGOS_GMAIL_LABEL_IMAGEN_4
                        final_label_reason = "paso_2_d"

                if not final_label_name:
                    if not candidatos and multipage_pdf_omitidos == 0:
                        final_label_name = PAGOS_GMAIL_LABEL_TEXTO
                        final_label_reason = "fallback_texto"
                    elif remitente_solo_master and not fully_digitized_email:
                        final_label_name = PAGOS_GMAIL_LABEL_MASTER
                        final_label_reason = "fallback_master"
                    elif not remitente_en_clientes:
                        final_label_name = PAGOS_GMAIL_LABEL_ERROR_EMAIL
                        final_label_reason = "fallback_error_email"
                    elif candidatos:
                        final_label_name = PAGOS_GMAIL_LABEL_MANUAL
                        final_label_reason = "fallback_manual"

                if final_label_name and final_label_name in PAGOS_GMAIL_ETIQUETAS_FINALES_PERMITIDAS:
                    if final_label_name not in plantilla_label_cache:
                        plantilla_label_cache[final_label_name] = ensure_user_label_id(
                            gmail_svc, final_label_name
                        )
                    final_label_id = plantilla_label_cache.get(final_label_name)
                    if final_label_id:
                        add_message_user_labels_only(gmail_svc, msg_id, [final_label_id])
                        run_stats["messages_final_label_applied"] += 1
                        _k = f"final_{final_label_reason}"
                        if _k in run_stats:
                            run_stats[_k] += 1
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiqueta final=%s (%s) msg=%s",
                            final_label_name,
                            final_label_reason,
                            msg_id,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta final %s",
                            final_label_name,
                        )
                elif candidatos:
                    run_stats["messages_no_final_label"] += 1
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: sin etiqueta final aplicable pese a candidatos (msg=%s)",
                        msg_id,
                    )

                if was_unread:
                    mark_as_read(gmail_svc, msg_id)

                if pending_gmail_temporal_delete_ids:
                    _ids_retry = sorted(pending_gmail_temporal_delete_ids)
                    try:
                        db.execute(
                            delete(GmailTemporal).where(
                                GmailTemporal.id.in_(_ids_retry)
                            )
                        )
                        db.commit()
                        logger.info(
                            "[PAGOS_GMAIL] Reintento limpieza gmail_temporal OK: %d id(s)",
                            len(_ids_retry),
                        )
                        pending_gmail_temporal_delete_ids.difference_update(_ids_retry)
                    except Exception as _retry_del_exc:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        logger.warning(
                            "[PAGOS_GMAIL] Reintento limpieza gmail_temporal falló (%d id(s)): %s",
                            len(_ids_retry),
                            _retry_del_exc,
                        )

                emails_ok += 1

                sync.emails_processed = emails_ok
                sync.files_processed = files_ok
                db.commit()

        messages = fetch_sorted_batch()
        run_stats["gmail_messages_listed"] = len(messages)
        if not messages:
            logger.info("[PAGOS_GMAIL] No hay correos con filtro %s", scan_filter)
        else:
            process_message_batch(messages, "run")

        try:
            redig_raw = list_messages_by_filter(
                gmail_svc, "manual_error_email_redigitaliza"
            )
            redig_messages = _sort_messages_inbox_primero_a_ultimo(
                _dedupe_messages_pagos_gmail(redig_raw)
            )
            run_stats["manual_error_redigitaliza_listed"] = len(redig_messages)
            if redig_messages:
                logger.warning(
                    "[PAGOS_GMAIL] Paso final redigitalizacion MANUAL+ERROR EMAIL: %d mensaje(s) listado(s)",
                    len(redig_messages),
                )
                try:
                    process_message_batch(
                        redig_messages,
                        "redig_manual_error_email",
                        redig_manual_error_pass=True,
                    )
                except Exception as _redig_pb_err:
                    logger.exception(
                        "[PAGOS_GMAIL] Paso redig MANUAL+ERROR: fallo procesando lote: %s",
                        _redig_pb_err,
                    )
                    run_stats["manual_error_redigitaliza_error"] = str(_redig_pb_err)[
                        :500
                    ]
        except PagosGmailGmailListError as _redig_list_err:
            logger.warning(
                "[PAGOS_GMAIL] Paso redig MANUAL+ERROR: listado Gmail omitido: %s",
                _redig_list_err,
            )
        except Exception as _redig_exc:
            logger.exception(
                "[PAGOS_GMAIL] Paso redig MANUAL+ERROR: error no esperado: %s",
                _redig_exc,
            )

        _pagos_metrics = _metricas_resumen_corrida_gmail_pagos(db, sync_id)
        _run_summary_ok = {
            "scan_filter": scan_filter,
            "gmail_messages_listed": run_stats["gmail_messages_listed"],
            "messages_skipped_invalid_sender": run_stats[
                "messages_skipped_invalid_sender"
            ],
            "messages_skipped_drive_folder": run_stats[
                "messages_skipped_drive_folder"
            ],
            "messages_skipped_clasificacion_etiqueta": run_stats[
                "messages_skipped_clasificacion_etiqueta"
            ],
            "messages_final_label_applied": run_stats["messages_final_label_applied"],
            "messages_no_final_label": run_stats["messages_no_final_label"],
            "final_paso_1_a": run_stats["final_paso_1_a"],
            "final_paso_1_b": run_stats["final_paso_1_b"],
            "final_paso_2_c": run_stats["final_paso_2_c"],
            "final_paso_2_d": run_stats["final_paso_2_d"],
            "final_fallback_texto": run_stats["final_fallback_texto"],
            "final_fallback_master": run_stats["final_fallback_master"],
            "final_fallback_error_email": run_stats["final_fallback_error_email"],
            "final_fallback_manual": run_stats["final_fallback_manual"],
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
            "manual_error_redigitaliza_listed": run_stats[
                "manual_error_redigitaliza_listed"
            ],
            "manual_error_redigitaliza_error": run_stats.get(
                "manual_error_redigitaliza_error"
            )
            or None,
            "gemini_model": _gemini_model_snapshot,
            **_pagos_metrics,
        }
        logger.info(
            "[PAGOS_GMAIL] FIN pipeline: correos=%d comprobantes=%d archivos=%d | "
            "alta_automatica_ok=%d pendientes_revision_excel=%d (sync_id=%s)",
            emails_ok,
            _pagos_metrics["comprobantes_digitados"],
            files_ok,
            _pagos_metrics["pagos_validos_alta_automatica"],
            _pagos_metrics["pagos_invalidos_pendientes_revision"],
            sync_id,
        )

        _persistir_estado_sync_pipeline_terminal(
            db,
            sync_id=sync_id,
            status="success",
            emails_ok=emails_ok,
            files_ok=files_ok,
            correos_marcados_revision=correos_marcados_revision,
            run_summary=_run_summary_ok,
            error_message=None,
        )
        return sync_id, "success"

    except PagosGmailGmailListError as e:
        logger.error(
            "[PAGOS_GMAIL] Fallo API Gmail al listar metadatos (sync=error; no es inbox vacio): %s",
            e,
        )
        _pagos_metrics_err = _metricas_resumen_corrida_gmail_pagos(db, sync_id)
        _run_summary_list_err = {
            "scan_filter": scan_filter,
            "gmail_messages_listed": run_stats["gmail_messages_listed"],
            "messages_skipped_invalid_sender": run_stats[
                "messages_skipped_invalid_sender"
            ],
            "messages_skipped_drive_folder": run_stats[
                "messages_skipped_drive_folder"
            ],
            "messages_skipped_clasificacion_etiqueta": run_stats[
                "messages_skipped_clasificacion_etiqueta"
            ],
            "messages_final_label_applied": run_stats["messages_final_label_applied"],
            "messages_no_final_label": run_stats["messages_no_final_label"],
            "final_paso_1_a": run_stats["final_paso_1_a"],
            "final_paso_1_b": run_stats["final_paso_1_b"],
            "final_paso_2_c": run_stats["final_paso_2_c"],
            "final_paso_2_d": run_stats["final_paso_2_d"],
            "final_fallback_texto": run_stats["final_fallback_texto"],
            "final_fallback_master": run_stats["final_fallback_master"],
            "final_fallback_error_email": run_stats["final_fallback_error_email"],
            "final_fallback_manual": run_stats["final_fallback_manual"],
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
            "manual_error_redigitaliza_listed": run_stats[
                "manual_error_redigitaliza_listed"
            ],
            "list_error": True,
            "gemini_model": _gemini_model_snapshot,
            **_pagos_metrics_err,
        }
        _persistir_estado_sync_pipeline_terminal(
            db,
            sync_id=sync_id,
            status="error",
            emails_ok=emails_ok,
            files_ok=files_ok,
            correos_marcados_revision=correos_marcados_revision,
            run_summary=_run_summary_list_err,
            error_message=str(e)[:2000],
        )
        return sync_id, "error"

    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Pipeline error inesperado: %s", e)
        _pagos_metrics_pipe = _metricas_resumen_corrida_gmail_pagos(db, sync_id)
        _run_summary_pipe_err = {
            "scan_filter": scan_filter,
            "gmail_messages_listed": run_stats["gmail_messages_listed"],
            "messages_skipped_invalid_sender": run_stats[
                "messages_skipped_invalid_sender"
            ],
            "messages_skipped_drive_folder": run_stats[
                "messages_skipped_drive_folder"
            ],
            "messages_skipped_clasificacion_etiqueta": run_stats[
                "messages_skipped_clasificacion_etiqueta"
            ],
            "messages_final_label_applied": run_stats["messages_final_label_applied"],
            "messages_no_final_label": run_stats["messages_no_final_label"],
            "final_paso_1_a": run_stats["final_paso_1_a"],
            "final_paso_1_b": run_stats["final_paso_1_b"],
            "final_paso_2_c": run_stats["final_paso_2_c"],
            "final_paso_2_d": run_stats["final_paso_2_d"],
            "final_fallback_texto": run_stats["final_fallback_texto"],
            "final_fallback_master": run_stats["final_fallback_master"],
            "final_fallback_error_email": run_stats["final_fallback_error_email"],
            "final_fallback_manual": run_stats["final_fallback_manual"],
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
            "manual_error_redigitaliza_listed": run_stats[
                "manual_error_redigitaliza_listed"
            ],
            "pipeline_error": True,
            "gemini_model": _gemini_model_snapshot,
            **_pagos_metrics_pipe,
        }
        _persistir_estado_sync_pipeline_terminal(
            db,
            sync_id=sync_id,
            status="error",
            emails_ok=emails_ok,
            files_ok=files_ok,
            correos_marcados_revision=correos_marcados_revision,
            run_summary=_run_summary_pipe_err,
            error_message=str(e)[:2000],
        )
        return sync_id, "error"
