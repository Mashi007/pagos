"""
Orquestacion: Gmail -> Gemini/BD por **cada adjunto elegible** (remitente en clientes), una fila Excel/BD por comprobante OK.
  -> flush sync_item + temporal -> comprobante en pago_comprobante_imagen (reuso por SHA-256 en la misma corrida) + URL en drive_link -> un solo commit; si falla el binario, rollback de esas filas.
  No hay subidas a Google Drive: el comprobante queda en BD; no se archiva .eml en Drive (drive_email_link sin uso).
  Si no cumple plantillas 1/2/3/4 o faltan datos -> no fila ni comprobante en BD para ese adjunto.

**Re-proceso innegociable:** si el mensaje tiene **cualquier etiqueta de usuario** Gmail (API ``type=user``), el pipeline **no** vuelve a escanear ni escribe filas Excel/BD, **salvo** modo ``scan_filter=error_email_rescan`` cuando **solo** esta la etiqueta **ERROR EMAIL** (re-lectura A/B). Cualquier otra etiqueta de usuario (o ERROR EMAIL junto con otra) implica pasar por alto. Sin etiquetas de usuario: solo sistema (INBOX, UNREAD, CATEGORY_*, etc.). Para reintentar: quitar etiquetas de usuario en Gmail. Si falla el catalogo de etiquetas en la API, se registra metrica y **no** se omite por etiqueta (evitar falsos negativos).

**Regla estricta (1 página por binario):** solo se digitaliza **una página** por archivo: imágenes tal cual; PDF solo si tiene **exactamente 1 página**. PDF con **2+ páginas** no se envía a Gemini; el hilo recibe etiqueta Gmail **PAGINAS** (puede convivir con otras etiquetas del mismo paso salvo la regla exclusiva de ERROR EMAIL abajo).

**Primera regla (remitente vs tabla clientes):** se compara el correo del **De (From)** con `clientes.email` y, si no coincide, con `clientes.email_secundario` (trim, minúsculas).
Si **coincide** (cédula resuelta): aplica digitalización por cada candidato (Gemini), filas Excel/BD y el resto de etiquetas (**MERCANTIL**/**BNC**/**BINANCE**/**BNV**, **MASTER**, **MANUAL**, **OTROS**, **PAGINAS**/**CALIDAD**/**TEXTO** si hubo PDF multipágina, imagen ilegible / no inventar, o **sin** imagen/PDF de comprobante (solo texto u adjuntos no imagen/PDF), etc., según corresponda).
Si **no** coincide o falla la consulta a `clientes`: **no** Gemini, **no** filas en `pagos_gmail_sync_item` / `gmail_temporal` ni comprobante en BD; en Gmail **únicamente** la etiqueta de usuario **ERROR EMAIL** (ninguna otra etiqueta de clasificación en ese paso), salvo **PAGINAS** si en el mensaje hubo PDF de 2+ páginas y **TEXTO** si no hay binario imagen/PDF de comprobante.
Si en un mensaje aplica **ERROR EMAIL** en Gmail: **solo ERROR EMAIL** en esa aplicación (salvo **PAGINAS**/**CALIDAD**/**TEXTO** añadidas aparte si aplica), nunca combinada con MERCANTIL/MANUAL/OTROS/etc.
Si **sí** hay coincidencia de remitente en clientes: aplican el resto de reglas (plantillas, MASTER para **master@rapicreditca.com**, etc.). Re-lectura cédula A/B desde la imagen: solo con **scan_filter=error_email_rescan**; si la cédula en imagen sigue ilegible (**ERROR** en columna), se aplica etiqueta **CALIDAD** en Gmail.
Remitente **master@rapicreditca.com** con fila en clientes: en Gmail solo etiqueta **MASTER** (sin MERCANTIL / BNC / BINANCE / BNV ni ERROR EMAIL).
Remitente **master@rapicreditca.com** **sin** fila en clientes: aplica la primera regla (**solo ERROR EMAIL** en Gmail; no **MASTER**).
Si en un mismo correo hay **varios** comprobantes digitalizados OK de tipos distintos (**A**/**B**/**C**/**D**/**NR**), en Gmail **solo** la etiqueta **MANUAL** (sin MERCANTIL/BNC/BINANCE/BNV, sin MASTER, sin ERROR EMAIL en esa aplicacion; **PAGINAS**/**CALIDAD**/**TEXTO** siguen aparte si aplica).
Etiquetas Gmail MERCANTIL (A) / BNC (B) / BINANCE (C) / BNV (D) solo con remitente en clientes y si el correo cumple al 100% en todos los candidatos procesados: cada candidato (1 pág.) debe ser
plantilla A o B con fecha/monto/ref + cedula resuelta, o plantilla C con monto/ref + cedula resuelta;
fecha de C = fecha del correo; cedula = lookup en tabla clientes por email De (From): primero `email`, luego `email_secundario`.
Si hay remitente en clientes pero la columna cédula queda en **ERROR EMAIL** (sin resolver por lookup): en Gmail **solo ERROR EMAIL** (sin otras etiquetas en la misma aplicación); **no** fila en `pagos_gmail_sync_item` / `gmail_temporal` ni en Excel (la literal ERROR EMAIL no se exporta).
Si falla la consulta a clientes: mismo bloqueo que remitente sin match (sin digitalizar ni Excel); Gmail **solo ERROR EMAIL**.
Etiqueta Gmail **OTROS** (solo esa en su llamada a Gmail, salvo **PAGINAS**/**CALIDAD**/**TEXTO** aparte si aplica): unicamente si hay candidatos, remitente en clientes, **ningun** comprobante digitalizado OK como plantilla **A**/**B**/**C**/**D** (MERCANTIL/BNC/BINANCE/BNV) y ninguna otra etiqueta de clasificacion del pipeline se aplico ya en ese mensaje.
Si en cualquier archivo falta requisito o no es plantilla valida: no etiquetas de plantilla segun reglas; el mensaje que **entraba no leido** queda **leido** tras procesarlo en el escaneo (no se modifican estrellas: las deja el usuario). No inventar datos: Gemini ya devuelve NA si no hay certeza.
Excel: GET /pagos/gmail/download-excel (filtros `solo_duplicados_documento` / `excluir_duplicados_documento` para plantilla banco A–D vs `pagos.numero_documento`).
Reglas de negocio A/B/C/D (autoconciliado, cascada cuotas, duplicados): ver `plantilla_abcd_proceso_negocio.py`.
Cedula: en flujo normal solo desde tabla clientes por email del De (From): `email` y `email_secundario` (no desde la imagen).
Re-lectura cédula en imagen (Mercantil/BNC, plantillas **A** y **B**): solo si **scan_filter=error_email_rescan**. Gemini en modo A/B con cédula
desde imagen o columna **ERROR**; si sigue ilegible, etiqueta **CALIDAD**.
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.gmail_abcd_cuotas_traza import (
    registrar_traza_gmail_abcd_cuotas_evento,
)
from app.services.pagos_gmail.pago_abcd_auto_service import (
    crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd,
)
from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    es_plantilla_banco_abcd,
    item_sync_abcd_candidato_revision_duplicado,
    resumen_log_linea_plantilla_abcd,
)
from app.services.pagos_gmail.gmail_service import (
    add_message_user_labels_only,
    build_gmail_service,
    ensure_user_label_id,
    get_pagos_gmail_image_pdf_files_for_pipeline,
    get_message_date,
    get_message_full_payload,
    get_existing_user_label_id,
    get_or_create_pagos_gmail_plantilla_label_ids,
    list_gmail_user_label_ids,
    list_messages_by_filter,
    mark_as_read,
    PagosGmailGmailListError,
    PAGOS_GMAIL_LABEL_ERROR_EMAIL,
    PAGOS_GMAIL_LABEL_OTROS,
    PAGOS_GMAIL_LABEL_MANUAL,
    PAGOS_GMAIL_LABEL_MASTER,
    PAGOS_GMAIL_LABEL_IMAGEN_1,
    PAGOS_GMAIL_LABEL_IMAGEN_2,
    PAGOS_GMAIL_LABEL_IMAGEN_3,
    PAGOS_GMAIL_LABEL_IMAGEN_4,
    PAGOS_GMAIL_LABEL_PAGINAS,
    PAGOS_GMAIL_LABEL_CALIDAD,
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
    Solo se escanea (Gemini) si el **De** está en `clientes` (email o email_secundario); **cada** adjunto de una sola página (imagen o PDF de 1 pág.) es un candidato y puede generar una fila. PDF con 2+ páginas no se digitaliza; se aplica etiqueta **PAGINAS** en Gmail.     Imagen ilegible / no inventar (p. ej. Gemini sin plantilla o columnas de imagen incompletas con cédula de cliente OK): **CALIDAD**. Sin binario imagen/PDF de comprobante (solo texto u otros adjuntos): **TEXTO**.
    Si no hay match en clientes (o fallo al consultar): **no** Gemini ni filas Excel/BD; Gmail **ERROR EMAIL** (y **PAGINAS** si hubo PDF multipágina; **TEXTO** si no hay imagen/PDF de pago).
    Por adjunto OK con remitente en tabla clientes: etiqueta MERCANTIL (A), BNC (B), BINANCE (C) o BNV (D) si **todo** el correo es del mismo tipo (A/B/C/D/NR);
    si hay **mas de un tipo** entre A, B, C, D y NR digitalizados OK: en Gmail **solo** etiqueta **MANUAL** (sin MERCANTIL/BNC/BINANCE/BNV ni MASTER ni ERROR EMAIL en esa llamada). Cierre: leido si hubo digitalizacion 100%% OK.
    Primera regla: sin coincidencia en `clientes.email` / `email_secundario` (o fallo al consultar): solo **ERROR EMAIL** en Gmail y sin filas (salvo **PAGINAS**/**TEXTO** si aplica). Con coincidencia: plantillas/MANUAL/**OTROS** (solo si no hubo A/B/C/D digitalizado OK)/**PAGINAS**/**CALIDAD**/**TEXTO**/etc.
    Cuando aplica **ERROR EMAIL** en Gmail: esa etiqueta en la llamada de error (no MERCANTIL, ni MANUAL, ni OTROS), salvo que prevalezca **solo MANUAL** por mezcla de tipos; **PAGINAS**/**CALIDAD**/**TEXTO** se añaden en paso aparte si aplica.
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (por defecto API/UI: all).
      Por defecto (**all** / **pending_identification**): inbox con imagen/PDF — leidos y no leidos (el pipeline no modifica estrellas Gmail),
      con cualquier etiqueta de usuario (incluye **ERROR EMAIL**; la consulta Gmail no excluye esa etiqueta).
      **unread** / **read**: mismo criterio base + ``is:unread`` / ``is:read`` en la búsqueda Gmail; los que entran como no leidos se marcan **leidos** al procesarlos en la corrida.
      **error_email_rescan**: listado ERROR EMAIL + media; se procesan mensajes cuya **unica** etiqueta de usuario sea **ERROR EMAIL**; si hay mas etiquetas de usuario, se omiten.
      pending_identification es alias del listado base (nombre conservado para scheduler/API).
    Orden comprobantes OK: insert sync_item + gmail_temporal -> flush -> persistir binario (o reuso SHA-256 en corrida) y URL en drive_link -> commit atomico.
    Los mensajes de cada corrida se listan **todos** los que cumplen el criterio **q** (paginacion Gmail hasta agotar nextPageToken),
    se ordenan como bandeja tipica (**mas reciente primero**, mas antiguo al final) y se procesan en ese orden del primero al ultimo.
    Una sola pasada de listado+proceso por ejecucion (salvo reintentos manuales).
    Cada mensaje que **entraba no leido** (labelIds al listar) se marca **leido** al terminar de procesarlo en esa corrida.
    Mensajes con etiquetas de usuario Gmail se omiten salvo **solo ERROR EMAIL** en modo ``error_email_rescan``. Fallo al listar catalogo de etiquetas: metrica ``gmail_labels_list_failed`` y no se aplica omision por etiqueta.
    Dedupe en la misma corrida: mismo binario de adjunto (SHA-256) tras un commit BD previo en ese run omite Gemini/BD/enlace
    (reenvios o mensajes duplicados con el mismo JPG/PDF).
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
                    sync_row.finished_at = datetime.now(timezone.utc)
                    sync_row.error_message = "no_credentials"
                    db.commit()
            except Exception:
                pass
        logger.warning("[PAGOS_GMAIL] Sin credenciales; pipeline abortado")
        return existing_sync_id, "no_credentials"

    logger.info("[PAGOS_GMAIL] Credenciales OK; construyendo servicio Gmail")
    gmail_svc = build_gmail_service(creds)
    logger.info("[PAGOS_GMAIL] Servicio Gmail construido (pipeline sin Google Drive)")

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
    # Mismo binario de comprobante en varios mensajes Gmail (reenvíos / hilos duplicados): una sola pasada Gemini+BD por corrida.
    seen_attachment_sha256: set[str] = set()
    # Misma corrida: varias filas Excel apuntando al mismo BLOB (mismo SHA-256) sin duplicar pago_comprobante_imagen.
    comprobante_reuse_por_sha256: dict[str, tuple[str, str]] = {}
    # Métricas para GET /pagos/gmail/status → last_run_summary (diagnóstico en toast UI).
    run_stats: dict[str, int] = {
        "gmail_messages_listed": 0,
        "messages_skipped_invalid_sender": 0,
        "messages_skipped_drive_folder": 0,
        "messages_skipped_clasificacion_etiqueta": 0,
        "gmail_labels_list_failed": 0,
    }

    try:
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

        def process_message_batch(batch: list[dict], label: str) -> None:
            nonlocal emails_ok, files_ok, correos_marcados_revision
            if batch:
                    logger.info(
                    "[PAGOS_GMAIL] Procesando lote %s: %d correos (imagen/PDF pipeline, formatos A/B/C/D)",
                    label,
                    len(batch),
                )
            # Etiquetas type=user: no re-escaneo, salvo solo ERROR EMAIL en error_email_rescan.
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
            _err_email_label_id: Optional[str] = None
            if error_email_rescan:
                _err_email_label_id = get_existing_user_label_id(
                    gmail_svc, PAGOS_GMAIL_LABEL_ERROR_EMAIL
                )

            for msg_info in batch:
                msg_id = msg_info["id"]
                label_ids_snapshot = list(msg_info.get("label_ids") or [])
                was_unread = "UNREAD" in label_ids_snapshot
                msg_lids_set = frozenset(label_ids_snapshot)
                _user_on_msg = msg_lids_set & _gmail_user_label_ids
                _skip_por_etiquetas_usuario = False
                if _labels_catalog_ok and _user_on_msg:
                    if (
                        error_email_rescan
                        and _err_email_label_id
                        and _user_on_msg.issubset(frozenset({_err_email_label_id}))
                    ):
                        _skip_por_etiquetas_usuario = False
                    else:
                        _skip_por_etiquetas_usuario = True
                if _skip_por_etiquetas_usuario:
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

                # Mercantil/BNC (A/B): cédula desde imagen solo con scan_filter **error_email_rescan**.
                modo_ab_cedula_desde_imagen = error_email_rescan
                if modo_ab_cedula_desde_imagen:
                    logger.info(
                        "[PAGOS_GMAIL]   Modo cedula imagen A/B (scan_filter=error_email_rescan); msg=%s",
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
                gmail_etiqueta_clasificacion_aplicada = False
                any_etiqueta_calidad_imagen = False
                if not candidatos:
                    any_incomplete_or_skipped = True
                tiene_medio_pipeline = bool(candidatos) or multipage_pdf_omitidos > 0

                if not remitente_en_clientes and candidatos:
                    logger.info(
                        "[PAGOS_GMAIL]   Remitente no en clientes.email/email_secundario (o fallo al consultar): "
                        "sin Gemini ni filas Excel/BD; Gmail solo ERROR EMAIL (msg_id=%s).",
                        msg_id,
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
                for filename, content, mime_type, origen_binario in (
                    [] if not remitente_en_clientes else candidatos
                ):
                    try:
                        body_bin = (
                            content
                            if isinstance(content, (bytes, bytearray))
                            else bytes(content)
                        )
                        file_digest = hashlib.sha256(body_bin).hexdigest()
                        if file_digest in seen_attachment_sha256:
                            logger.info(
                                "[PAGOS_GMAIL]   Dedupe: bytes identicos a comprobante ya digitalizado antes en esta corrida "
                                "(sha256=%s…) — sin Gemini/BD: %s",
                                file_digest[:16],
                                filename,
                            )
                            any_incomplete_or_skipped = True
                            continue

                        fmt, data = classify_and_extract_pagos_gmail_attachment(
                            content,
                            filename,
                            remitente_correo_header=from_h,
                            origen_binario=origen_binario,
                            modo_error_email_ab=modo_ab_cedula_desde_imagen,
                        )

                        if fmt not in PAGOS_GMAIL_FORMATOS_PLANTILLA:
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            any_etiqueta_calidad_imagen = True
                            logger.warning(
                                "[PAGOS_GMAIL]   No es plantilla A/B/C/D - no BD: %s",
                                filename,
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
                        elif modo_ab_cedula_desde_imagen and fmt in ("A", "B"):
                            f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                            m = _v(data.get("monto"))
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            c = _cedula_desde_imagen_rescan_error_email(data.get("cedula"))
                            c_ok = True
                            if c == PAGOS_GMAIL_ERROR_CEDULA_IMAGEN:
                                any_etiqueta_calidad_imagen = True
                            logger.info(
                                "[PAGOS_GMAIL]   Re-scan ERROR EMAIL (%s): columna Cedula desde imagen=%s archivo=%s",
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
                                if c_ok:
                                    any_etiqueta_calidad_imagen = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   Formato NR pero fila incompleta (monto!=NR o cedula vacia) - no BD: %s",
                                    filename,
                                )
                                continue
                        elif not _campos_completos(f, c, m, r):
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            if c_ok:
                                any_etiqueta_calidad_imagen = True
                            logger.warning(
                                "[PAGOS_GMAIL]   Plantilla %s pero columnas incompletas - no BD: %s",
                                fmt,
                                filename,
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
                        pending.append(
                            {
                                "fmt": fmt,
                                "f": f,
                                "c": c,
                                "m": m,
                                "r": r,
                                "banco_excel": banco_excel,
                                "filename": filename,
                                "content": content,
                                "mime_type": mime_type,
                                "sha256": file_digest,
                            }
                        )
                    except Exception as e:
                        logger.warning("[PAGOS_GMAIL]   Error procesando %s: %s", filename, e)
                        any_incomplete_or_skipped = True
                        any_skipped_not_plantilla_o_campos = True

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
                                    and remitente_en_clientes
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
                                                seen_attachment_sha256.add(k)
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
                mezcla_tipos_banco_mismo_correo = (
                    remitente_en_clientes and len(tipos_digitados_distintos) > 1
                )
                if mezcla_tipos_banco_mismo_correo:
                    label_ids_for_message.clear()
                    logger.info(
                        "[PAGOS_GMAIL]   Varios tipos de comprobante en un correo (%s) -> "
                        "Gmail MANUAL (sin MERCANTIL/BNC/BINANCE/BNV conjuntos)",
                        ", ".join(sorted(tipos_digitados_distintos)),
                    )
                plantilla_unique_ids = list(
                    dict.fromkeys(x for x in label_ids_for_message if x)
                )
                gmail_label_id_manual_mezcla: Optional[str] = None
                if mezcla_tipos_banco_mismo_correo:
                    k_man_mz = PAGOS_GMAIL_LABEL_MANUAL
                    if k_man_mz not in plantilla_label_cache:
                        plantilla_label_cache[k_man_mz] = ensure_user_label_id(
                            gmail_svc, k_man_mz
                        )
                    gmail_label_id_manual_mezcla = plantilla_label_cache.get(k_man_mz)
                    if not gmail_label_id_manual_mezcla:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s (mezcla tipos)",
                            k_man_mz,
                        )
                # Mezcla A/B/C/D/NR en un solo correo: en Gmail **solo** MANUAL (sin MERCANTIL/BNC/BINANCE/BNV ni MASTER ni ERROR EMAIL).
                mezcla_solo_manual_gmail = bool(
                    mezcla_tipos_banco_mismo_correo and gmail_label_id_manual_mezcla
                )
                # ERROR EMAIL: si aplica, en Gmail solo esa etiqueta (no combinar con plantillas ni MANUAL).
                gmail_label_id_error_email: Optional[str] = None
                if (
                    (
                        (not remitente_en_clientes)
                        or (
                            any_cedula_lookup_failed
                            and committed_comprobante_rows
                        )
                    )
                    and not (remitente_solo_master and remitente_en_clientes)
                    and not mezcla_solo_manual_gmail
                ):
                    k_err = PAGOS_GMAIL_LABEL_ERROR_EMAIL
                    if k_err not in plantilla_label_cache:
                        plantilla_label_cache[k_err] = ensure_user_label_id(
                            gmail_svc, k_err
                        )
                    err_lid = plantilla_label_cache.get(k_err)
                    if err_lid:
                        gmail_label_id_error_email = err_lid
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: se aplicara etiqueta %s (remitente sin fila en clientes, "
                            "o cedula no resuelta con filas comprobante confirmadas)",
                            k_err,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s — revisar permisos Gmail",
                            k_err,
                        )

                gmail_precursor_label_ids = (
                    [gmail_label_id_error_email] if gmail_label_id_error_email else []
                )

                if (
                    remitente_solo_master
                    and remitente_en_clientes
                    and candidatos
                ):
                    k_master = PAGOS_GMAIL_LABEL_MASTER
                    if k_master not in plantilla_label_cache:
                        plantilla_label_cache[k_master] = ensure_user_label_id(
                            gmail_svc, k_master
                        )
                    id_master = plantilla_label_cache.get(k_master)
                    if id_master:
                        if fully_digitized_email:
                            if mezcla_solo_manual_gmail:
                                batch_master = [gmail_label_id_manual_mezcla]
                            else:
                                batch_master = list(
                                    dict.fromkeys(
                                        [
                                            *gmail_precursor_label_ids,
                                            id_master,
                                            *(
                                                [gmail_label_id_manual_mezcla]
                                                if gmail_label_id_manual_mezcla
                                                else []
                                            ),
                                        ]
                                    )
                                )
                            if batch_master:
                                add_message_user_labels_only(
                                    gmail_svc, msg_id, batch_master
                                )
                            gmail_etiqueta_clasificacion_aplicada = True
                            mark_as_read(gmail_svc, msg_id)
                            correos_marcados_revision += 1
                            if mezcla_solo_manual_gmail:
                                logger.info(
                                    "[PAGOS_GMAIL]   Gmail: %s — solo etiqueta %s (mezcla tipos; sin MASTER ni otras)",
                                    PAGOS_GMAIL_SENDER_MASTER,
                                    PAGOS_GMAIL_LABEL_MANUAL,
                                )
                            else:
                                logger.info(
                                    "[PAGOS_GMAIL]   Gmail: %s — etiqueta %s aplicada; total etiquetas Gmail en hilo=%d (100%% OK)",
                                    PAGOS_GMAIL_SENDER_MASTER,
                                    k_master,
                                    len(batch_master),
                                )
                        else:
                            if mezcla_solo_manual_gmail:
                                batch_master_partial = [gmail_label_id_manual_mezcla]
                            else:
                                batch_master_partial = list(
                                    dict.fromkeys(
                                        [
                                            id_master,
                                            *(
                                                [gmail_label_id_manual_mezcla]
                                                if gmail_label_id_manual_mezcla
                                                else []
                                            ),
                                        ]
                                    )
                                )
                            add_message_user_labels_only(
                                gmail_svc, msg_id, batch_master_partial
                            )
                            gmail_etiqueta_clasificacion_aplicada = True
                            if mezcla_solo_manual_gmail:
                                logger.info(
                                    "[PAGOS_GMAIL]   Gmail: %s — solo etiqueta %s (mezcla tipos)",
                                    PAGOS_GMAIL_SENDER_MASTER,
                                    PAGOS_GMAIL_LABEL_MANUAL,
                                )
                            else:
                                logger.info(
                                    "[PAGOS_GMAIL]   Gmail: %s — %s (sin MERCANTIL / BNC / BINANCE / BNV / ERROR EMAIL)",
                                    PAGOS_GMAIL_SENDER_MASTER,
                                    ", ".join(
                                        [k_master]
                                        + (
                                            [PAGOS_GMAIL_LABEL_MANUAL]
                                            if gmail_label_id_manual_mezcla
                                            else []
                                        )
                                    ),
                                )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_master,
                        )
                elif fully_digitized_email:
                    if mezcla_solo_manual_gmail:
                        batch_ok = [gmail_label_id_manual_mezcla]
                    elif gmail_label_id_error_email:
                        batch_ok = [gmail_label_id_error_email]
                    else:
                        batch_ok = list(
                            dict.fromkeys(
                                [
                                    *gmail_precursor_label_ids,
                                    *plantilla_unique_ids,
                                    *(
                                        [gmail_label_id_manual_mezcla]
                                        if gmail_label_id_manual_mezcla
                                        else []
                                    ),
                                ]
                            )
                        )
                    if batch_ok:
                        add_message_user_labels_only(gmail_svc, msg_id, batch_ok)
                    gmail_etiqueta_clasificacion_aplicada = True
                    mark_as_read(gmail_svc, msg_id)
                    correos_marcados_revision += 1
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: 100%% adjuntos OK — etiquetas usuario aplicadas: %d id(s)%s; leido",
                        len(batch_ok),
                        " (solo MANUAL por mezcla tipos)"
                        if mezcla_solo_manual_gmail
                        else (
                            " (solo ERROR EMAIL)"
                            if gmail_label_id_error_email
                            else " (plantilla/MANUAL)"
                        ),
                    )
                elif (
                    (committed_comprobante_rows or not remitente_en_clientes)
                    and (not remitente_solo_master or not remitente_en_clientes)
                    and (
                        gmail_precursor_label_ids
                        or plantilla_unique_ids
                        or gmail_label_id_manual_mezcla
                    )
                ):
                    if mezcla_solo_manual_gmail:
                        batch_partial = [gmail_label_id_manual_mezcla]
                    elif gmail_label_id_error_email:
                        batch_partial = [gmail_label_id_error_email]
                    else:
                        batch_partial = list(
                            dict.fromkeys(
                                [
                                    *gmail_precursor_label_ids,
                                    *plantilla_unique_ids,
                                    *(
                                        [gmail_label_id_manual_mezcla]
                                        if gmail_label_id_manual_mezcla
                                        else []
                                    ),
                                ]
                            )
                        )
                    if batch_partial:
                        add_message_user_labels_only(
                            gmail_svc, msg_id, batch_partial
                        )
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiquetas usuario aplicadas: %d id(s)%s",
                            len(batch_partial),
                            " (solo MANUAL por mezcla tipos)"
                            if mezcla_solo_manual_gmail
                            else (
                                " (solo ERROR EMAIL)"
                                if gmail_label_id_error_email
                                else " (plantilla/MANUAL)"
                            ),
                        )
                    if candidatos:
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: revision (no 100%% digitalizacion completa); "
                            "no leido -> leido al cerrar mensaje si aplicaba; estrellas no se modifican"
                        )
                elif candidatos:
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: revision (no 100%% digitalizacion o sin adjuntos validos); "
                        "no leido -> leido al cerrar mensaje si aplicaba; estrellas no se modifican"
                    )
                else:
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: filtro=%s — sin candidatos imagen/PDF utiles; "
                        "sin no-leido aqui (etiqueta TEXTO si aplica en paso final).",
                        scan_filter,
                    )

                tiene_plantilla_banco_abcd_digitada = any(
                    f in ("A", "B", "C", "D") for f in bank_fmts_digitized
                )
                if (
                    candidatos
                    and remitente_en_clientes
                    and not gmail_label_id_error_email
                    and not gmail_etiqueta_clasificacion_aplicada
                    and not tiene_plantilla_banco_abcd_digitada
                ):
                    k_otros = PAGOS_GMAIL_LABEL_OTROS
                    if k_otros not in plantilla_label_cache:
                        plantilla_label_cache[k_otros] = ensure_user_label_id(
                            gmail_svc, k_otros
                        )
                    otros_lid = plantilla_label_cache.get(k_otros)
                    if otros_lid:
                        add_message_user_labels_only(
                            gmail_svc, msg_id, [otros_lid]
                        )
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: solo etiqueta %s (sin plantilla A/B/C/D digitalizada; "
                            "sin MERCANTIL/BNC/BINANCE/BNV/MASTER/ERROR EMAIL en esta llamada)",
                            k_otros,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_otros,
                        )

                if multipage_pdf_omitidos > 0:
                    k_pag = PAGOS_GMAIL_LABEL_PAGINAS
                    if k_pag not in plantilla_label_cache:
                        plantilla_label_cache[k_pag] = ensure_user_label_id(
                            gmail_svc, k_pag
                        )
                    lid_pag = plantilla_label_cache.get(k_pag)
                    if lid_pag:
                        add_message_user_labels_only(gmail_svc, msg_id, [lid_pag])
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiqueta %s (%d PDF(s) con 2+ paginas; no digitalizados)",
                            k_pag,
                            multipage_pdf_omitidos,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_pag,
                        )

                if any_etiqueta_calidad_imagen and remitente_en_clientes:
                    k_cal = PAGOS_GMAIL_LABEL_CALIDAD
                    if k_cal not in plantilla_label_cache:
                        plantilla_label_cache[k_cal] = ensure_user_label_id(
                            gmail_svc, k_cal
                        )
                    lid_cal = plantilla_label_cache.get(k_cal)
                    if lid_cal:
                        add_message_user_labels_only(gmail_svc, msg_id, [lid_cal])
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiqueta %s (imagen ilegible / no inventar; "
                            "ninguno o datos incompletos desde pixeles)",
                            k_cal,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_cal,
                        )

                if not candidatos and multipage_pdf_omitidos == 0:
                    k_txt = PAGOS_GMAIL_LABEL_TEXTO
                    if k_txt not in plantilla_label_cache:
                        plantilla_label_cache[k_txt] = ensure_user_label_id(
                            gmail_svc, k_txt
                        )
                    lid_txt = plantilla_label_cache.get(k_txt)
                    if lid_txt:
                        add_message_user_labels_only(gmail_svc, msg_id, [lid_txt])
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiqueta %s (sin imagen/PDF de comprobante; "
                            "solo texto u adjuntos no extraibles como captura de pago)",
                            k_txt,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_txt,
                        )

                if was_unread:
                    mark_as_read(gmail_svc, msg_id)

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

        sync.finished_at = datetime.now(timezone.utc)
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        sync.run_summary = {
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
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
        }
        logger.info("[PAGOS_GMAIL] FIN pipeline: emails=%d filas=%d", emails_ok, files_ok)

        sync.status = "success"
        sync.error_message = None
        db.commit()
        return sync_id, sync.status

    except PagosGmailGmailListError as e:
        logger.error(
            "[PAGOS_GMAIL] Fallo API Gmail al listar metadatos (sync=error; no es inbox vacio): %s",
            e,
        )
        sync.finished_at = datetime.now(timezone.utc)
        sync.status = "error"
        sync.error_message = str(e)[:2000]
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        sync.run_summary = {
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
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
            "list_error": True,
        }
        db.commit()
        return sync_id, "error"

    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Pipeline error inesperado: %s", e)
        sync.finished_at = datetime.now(timezone.utc)
        sync.status = "error"
        sync.error_message = str(e)[:2000]
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        sync.run_summary = {
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
            "gmail_labels_list_failed": run_stats["gmail_labels_list_failed"],
            "pipeline_error": True,
        }
        db.commit()
        return sync_id, "error"
