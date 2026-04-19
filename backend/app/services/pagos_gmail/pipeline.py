"""
Orquestacion: Gmail -> Gemini/BD **solo** si el mensaje cumple regla inegociable **una sola pieza** (ver abajo); si no, sin escaneo ni filas comprobante.
  -> flush sync_item + temporal -> comprobante en pago_comprobante_imagen (reuso por SHA-256 en la misma corrida) + URL en drive_link -> un solo commit; si falla el binario, rollback de esas filas.
  No hay subidas a Google Drive: el comprobante queda en BD; no se archiva .eml en Drive (drive_email_link sin uso).
  Si no cumple plantillas 1/2/3/4 o faltan datos -> no fila ni comprobante en BD para ese adjunto.

**Primera regla (remitente vs tabla clientes):** se compara el correo del **De (From)** con `clientes.email` y, si no coincide, con `clientes.email_secundario` (trim, minúsculas).
Si **coincide** con alguno: aplican las reglas siguientes (Gemini/plantillas, **MERCANTIL**/**BNC**/**BINANCE**/**BNV**, **MASTER**, **MANUAL**, **OTROS**, etc., según corresponda).
Si **no** coincide (o falla la consulta a clientes): en Gmail **únicamente** la etiqueta de usuario **ERROR EMAIL** — no se puede aplicar **ninguna otra** etiqueta de clasificación en ese mensaje (ni MERCANTIL, ni **MANUAL**, ni **OTROS**, etc.). Sí puede seguir la generación de fila Excel / comprobante en BD si el comprobante es plantilla válida (columna Cédula ERROR EMAIL / ERROR BD).
Si en un mensaje aplica **ERROR EMAIL** en Gmail (incluido remitente sin match pero con filas comprobante): **solo ERROR EMAIL** en ese paso, nunca combinada con otras etiquetas.
Si **sí** hay coincidencia de remitente en clientes: aplican el resto de reglas (plantillas, MASTER para **master@rapicreditca.com**, etc.). Re-lectura cédula A/B desde la imagen: solo con **scan_filter=error_email_rescan** (no se añade etiqueta Gmail por ese re-escaneo).
Remitente **master@rapicreditca.com** con fila en clientes: en Gmail solo etiqueta **MASTER** (sin MERCANTIL / BNC / BINANCE / BNV ni ERROR EMAIL).
Remitente **master@rapicreditca.com** **sin** fila en clientes: aplica la primera regla (**solo ERROR EMAIL** en Gmail; no **MASTER**).
**Regla inegociable (una sola pieza):** tras expandir PDF, solo se procesa (Gemini, filas, comprobante en BD) si hay **exactamente un** candidato imagen/PDF **y** **ningún** PDF de más de una página omitido en ese mensaje. Si hay **0** candidatos pero sí PDF multipágina omitido(s), o **más de un** candidato, o **cualquier** PDF multipágina omitido junto a otros medios: **no** Gemini ni filas comprobante. En Gmail: con remitente en clientes **solo etiqueta MANUAL** (sin MERCANTIL/BNC/OTROS/MASTER ni otras); sin remitente en clientes **solo ERROR EMAIL** (sin MANUAL ni otras).
Si en un mismo correo hubiera **varios** comprobantes digitalizados OK de tipos distintos (**A**/**B**/**C**/**D**/**NR**), no MERCANTIL/BNC/BINANCE/BNV conjuntos y solo **MANUAL** (con cliente); con la regla **una sola pieza** ese caso no se da en el flujo actual (un solo candidato escaneable).
Etiquetas Gmail MERCANTIL (A) / BNC (B) / BINANCE (C) / BNV (D) solo con remitente en clientes y si el correo cumple al 100%: cada candidato imagen/PDF debe ser
plantilla A o B con fecha/monto/ref + cedula resuelta, o plantilla C con monto/ref + cedula resuelta;
fecha de C = fecha del correo; cedula = lookup en tabla clientes por email De (From): primero `email`, luego `email_secundario`.
Si hay cliente pero falla otro requisito de cédula en flujo normal: columna Cedula = ERROR EMAIL / ERROR BD según corresponda; en Gmail **solo ERROR EMAIL** (sin otras etiquetas en la misma aplicación).
Si falla la consulta a clientes: ERROR BD (misma etiqueta Gmail que ERROR EMAIL) y se trata como remitente no válido para el resto de etiquetas.
En ambos casos (3.3) igual se genera fila Excel y comprobante en BD si el comprobante es plantilla valida.
Si ninguna etiqueta de clasificacion aplica y el remitente está en clientes: etiqueta Gmail **OTROS** (con candidatos imagen/PDF).
Si en cualquier archivo falta requisito o no es plantilla valida: no etiquetas de plantilla; con candidatos imagen/PDF
se marca **no leido** en Gmail para reintento (no se modifican estrellas: las deja el usuario). No inventar datos: Gemini ya devuelve NA si no hay certeza.
Excel: GET /pagos/gmail/download-excel.
Cedula: en flujo normal solo desde tabla clientes por email del De (From): `email` y `email_secundario` (no desde la imagen).
Re-lectura cédula en imagen (Mercantil/BNC, plantillas **A** y **B**): solo si **scan_filter=error_email_rescan**. Gemini en modo A/B con cédula
desde imagen o columna **ERROR**; no se aplica ninguna etiqueta Gmail extra por ese re-escaneo.
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
from app.services.pagos_gmail.gmail_service import (
    add_message_user_labels_only,
    build_gmail_service,
    ensure_user_label_id,
    get_pagos_gmail_image_pdf_files_for_pipeline,
    get_message_date,
    get_message_full_payload,
    get_or_create_pagos_gmail_plantilla_label_ids,
    list_messages_by_filter,
    mark_as_read,
    mark_message_unread,
    PagosGmailGmailListError,
    PAGOS_GMAIL_LABEL_ERROR_EMAIL,
    PAGOS_GMAIL_LABEL_OTROS,
    PAGOS_GMAIL_LABEL_MANUAL,
    PAGOS_GMAIL_LABEL_MASTER,
    PAGOS_GMAIL_LABEL_IMAGEN_1,
    PAGOS_GMAIL_LABEL_IMAGEN_2,
    PAGOS_GMAIL_LABEL_IMAGEN_3,
    PAGOS_GMAIL_LABEL_IMAGEN_4,
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


def _sort_key_pagos_gmail_chrono_asc(m: dict) -> tuple:
    """
    Clave de orden cronologico ascendente (primero el mas antiguo, al final el mas reciente).
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


def _sort_messages_by_date_asc(messages: list[dict]) -> list[dict]:
    """Orden estable: del correo mas antiguo al mas reciente (ver _sort_key_pagos_gmail_chrono_asc)."""
    return sorted(messages, key=_sort_key_pagos_gmail_chrono_asc, reverse=False)


# Columna Excel "Banco" al digitalizar: imagen 1 (A) / imagen 2 (B) / imagen 3 Binance (C) / imagen 4 BDV (D).
PAGOS_GMAIL_BANCO_IMAGEN_1 = "Mercantil"
PAGOS_GMAIL_BANCO_IMAGEN_2 = "BNC"
PAGOS_GMAIL_BANCO_IMAGEN_3 = "BINANCE"
PAGOS_GMAIL_BANCO_IMAGEN_4 = "BDV"

# Columna Cedula en Excel cuando no se puede resolver por remitente (max 50 chars en modelo).
PAGOS_GMAIL_ERROR_CEDULA_BD = "ERROR BD"  # 3.1 fallo al consultar tabla clientes
PAGOS_GMAIL_ERROR_CEDULA_EMAIL = "ERROR EMAIL"  # 3.2 remitente sin fila en clientes
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
    Si no hay fila: ERROR EMAIL. Si falla la consulta: ERROR BD. (3.3 sigue generando fila en sync_item / comprobante en BD si plantilla OK.)
    """
    c_raw, motivo = _cedula_por_email_cliente(db, sender_lc)
    if c_raw:
        return formatear_cedula(c_raw), True
    if motivo == "BD":
        return PAGOS_GMAIL_ERROR_CEDULA_BD, False
    return PAGOS_GMAIL_ERROR_CEDULA_EMAIL, False


def run_pipeline(
    db: Session,
    existing_sync_id: Optional[int] = None,
    scan_filter: str = "all",
) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline Gmail -> Gemini -> BD (comprobante en pago_comprobante_imagen; sin subidas a Drive).
    Solo se escanea (Gemini) si hay **exactamente un** candidato y **cero** PDFs multipagina omitidos; si no, sin escaneo ni filas: **solo MANUAL** (remitente en clientes) o **solo ERROR EMAIL** (sin cliente), sin otras etiquetas en ese caso.
    Por adjunto OK con remitente en tabla clientes: etiqueta IMAGEN 1 (A), 2 (B), 3 (C) o 4 (D) si **todo** el correo es del mismo tipo (A/B/C/D/NR);
    si hay **mas de un tipo** entre A, B, C, D y NR digitalizados OK: **MANUAL** en Gmail (sin MERCANTIL/BNC/BINANCE/BNV). Cierre: leido si hubo digitalizacion 100%% OK.
    Primera regla: comparar email del remitente con `clientes.email` / `email_secundario`; si no coincide, solo **ERROR EMAIL** en Gmail (sin ninguna otra etiqueta en ese envío). Si coincide, reglas de plantillas/MANUAL/OTROS/etc.
    Cuando aplica **ERROR EMAIL** en Gmail: únicamente esa etiqueta en la llamada (no MERCANTIL, ni MANUAL, ni OTROS).
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (por defecto API/UI: all).
      Por defecto (**all** / **pending_identification**): inbox con imagen/PDF — leidos y no leidos (el pipeline no modifica estrellas Gmail),
      con cualquier etiqueta de usuario (incluye **ERROR EMAIL**; la consulta Gmail no excluye esa etiqueta).
      **unread** / **read**: mismo criterio base + ``is:unread`` / ``is:read`` en la búsqueda Gmail.
      **error_email_rescan**: lista Gmail con etiqueta ERROR EMAIL + media; Gemini en modo A/B leyendo cédula desde imagen.
      pending_identification es alias del listado base (nombre conservado para scheduler/API).
    Orden comprobantes OK: insert sync_item + gmail_temporal -> flush -> persistir binario (o reuso SHA-256 en corrida) y URL en drive_link -> commit atomico.
    Los mensajes de cada lote se ordenan por fecha del correo de mas antiguo a mas reciente antes de procesar.
    Una sola pasada de listado+proceso por ejecucion (salvo reintentos manuales).
    Tras listar **todos** los mensajes que cumplen el filtro (paginacion completa), se ordenan siempre del **mas antiguo al mas reciente**
    y se procesan en ese orden estricto (primer correo de la lista primero, ultimo al final).
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
            ordered = _sort_messages_by_date_asc(messages)
            logger.info(
                "[PAGOS_GMAIL] Correos (filtro=%s): %d — orden cronologico ascendente "
                "(internalDate Gmail si existe; si no cabecera Date). Procesamiento: del primero al ultimo de esta lista.",
                scan_filter,
                len(ordered),
            )
            if ordered:
                first = ordered[0]
                last = ordered[-1]
                logger.info(
                    "[PAGOS_GMAIL] Ventana ordenada: primero id=%s internalDate_ms=%s; "
                    "ultimo id=%s internalDate_ms=%s",
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
            for msg_info in batch:
                msg_id = msg_info["id"]
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
                if not candidatos:
                    any_incomplete_or_skipped = True
                tiene_medio_pipeline = bool(candidatos) or multipage_pdf_omitidos > 0
                escaneo_gemini_permitido = (
                    len(candidatos) == 1 and multipage_pdf_omitidos == 0
                )
                viola_regla_una_sola_pieza = (
                    tiene_medio_pipeline and not escaneo_gemini_permitido
                )
                if viola_regla_una_sola_pieza:
                    any_incomplete_or_skipped = True
                    logger.info(
                        "[PAGOS_GMAIL]   Regla una sola pieza: candidatos=%d multipag_omitidos=%d -> "
                        "sin Gemini ni filas comprobante; Gmail solo MANUAL (cliente) o solo ERROR EMAIL (sin cliente).",
                        len(candidatos),
                        multipage_pdf_omitidos,
                    )

                def _campos_completos(fecha: str, cedula: str, monto: str, ref: str) -> bool:
                    def ok(val: str) -> bool:
                        s = (val or "").strip()
                        return bool(s) and s.upper() != PAGOS_NA

                    return ok(fecha) and ok(cedula) and ok(monto) and ok(ref)

                def _campos_completos_nr(cedula: str, monto: str) -> bool:
                    """Fila NR: monto literal NR; cédula columna debe existir (cliente o ERROR EMAIL/BD)."""
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
                    [] if viola_regla_una_sola_pieza else candidatos
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
                        if fmt == "NR":
                            if not _campos_completos_nr(c, m):
                                any_incomplete_or_skipped = True
                                any_skipped_not_plantilla_o_campos = True
                                logger.warning(
                                    "[PAGOS_GMAIL]   Formato NR pero fila incompleta (monto!=NR o cedula vacia) - no BD: %s",
                                    filename,
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
                            comprobante_resueltos: list[tuple[str, str, dict]] = []
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
                                comprobante_resueltos.append((_uid, link_url or "", p))
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
                                    for uid, link_url, p in comprobante_resueltos:
                                        sh_raw = p.get("sha256")
                                        if isinstance(sh_raw, str) and len(sh_raw.strip()) == 64:
                                            k = sh_raw.strip().lower()
                                            if all(c in "0123456789abcdef" for c in k):
                                                seen_attachment_sha256.add(k)
                                                comprobante_reuse_por_sha256[k] = (uid, link_url)
                                        files_ok += 1
                                        had_complete_digitalization = True
                                        fmt = p["fmt"]
                                        if fmt in ("A", "B", "C", "D", "NR"):
                                            bank_fmts_digitized.append(fmt)
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
                            "remitente sin match en clientes (columna Cedula ERROR EMAIL/BD). "
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
                    remitente_en_clientes
                    and (not viola_regla_una_sola_pieza)
                    and len(tipos_digitados_distintos) > 1
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
                            "[PAGOS_GMAIL]   Gmail: se aplicara etiqueta %s (remitente sin fila en clientes, ERROR BD, "
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
                    and not viola_regla_una_sola_pieza
                ):
                    k_master = PAGOS_GMAIL_LABEL_MASTER
                    if k_master not in plantilla_label_cache:
                        plantilla_label_cache[k_master] = ensure_user_label_id(
                            gmail_svc, k_master
                        )
                    id_master = plantilla_label_cache.get(k_master)
                    if id_master:
                        if fully_digitized_email:
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
                            logger.info(
                                "[PAGOS_GMAIL]   Gmail: %s — etiqueta %s aplicada; total etiquetas Gmail en hilo=%d (100%% OK)",
                                PAGOS_GMAIL_SENDER_MASTER,
                                k_master,
                                len(batch_master),
                            )
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
                    if gmail_label_id_error_email:
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
                        " (solo ERROR EMAIL)" if gmail_label_id_error_email else " (plantilla/MANUAL)",
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
                    if gmail_label_id_error_email:
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
                            " (solo ERROR EMAIL)" if gmail_label_id_error_email else " (plantilla/MANUAL)",
                        )
                    if candidatos:
                        mark_message_unread(gmail_svc, msg_id)
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: hilo NO LEIDO (revision; no 100%% digitalizacion completa; "
                            "estrellas Gmail no se modifican)"
                        )
                elif viola_regla_una_sola_pieza and remitente_en_clientes:
                    k_man_mul = PAGOS_GMAIL_LABEL_MANUAL
                    if k_man_mul not in plantilla_label_cache:
                        plantilla_label_cache[k_man_mul] = ensure_user_label_id(
                            gmail_svc, k_man_mul
                        )
                    lid_mul = plantilla_label_cache.get(k_man_mul)
                    if lid_mul:
                        add_message_user_labels_only(gmail_svc, msg_id, [lid_mul])
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: solo etiqueta %s (regla una sola pieza; candidatos=%d multipag=%d)",
                            k_man_mul,
                            len(candidatos),
                            multipage_pdf_omitidos,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s (una sola pieza)",
                            k_man_mul,
                        )
                elif candidatos:
                    mark_message_unread(gmail_svc, msg_id)
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: hilo marcado NO LEIDO (no 100%% digitalizacion o sin adjuntos validos; "
                        "estrellas Gmail no se modifican — revision humana; el listado del pipeline incluye leidos y no leidos)"
                    )
                else:
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: filtro=%s — sin candidatos imagen/PDF utiles; "
                        "sin modificaciones en Gmail.",
                        scan_filter,
                    )

                if (
                    candidatos
                    and remitente_en_clientes
                    and not viola_regla_una_sola_pieza
                    and not gmail_label_id_error_email
                    and not gmail_etiqueta_clasificacion_aplicada
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
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiqueta %s (sin MERCANTIL/BNC/BINANCE/BNV/MASTER/ERROR EMAIL)",
                            k_otros,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_otros,
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
            "pipeline_error": True,
        }
        db.commit()
        return sync_id, "error"
