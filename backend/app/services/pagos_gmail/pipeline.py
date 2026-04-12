"""
Orquestacion: Gmail -> Gemini (toda imagen/PDF adjunta o en cuerpo/related/HTML/mixed + rfc822) -> plantilla A/B/C/D
  -> commit BD (fila sin enlaces Drive) -> subida Drive -> commit enlaces en BD.
  Asi no quedan archivos en Drive sin fila; los enlaces existen en BD justo despues del segundo commit.
  Si no cumple plantillas 1/2/3/4 o faltan datos -> no fila ni archivo en Drive para ese adjunto.

Remitente **master@rapicreditca.com**: en Gmail solo etiqueta **MASTER** (sin MERCANTIL / BNC / BINANCE / BNV ni ERROR EMAIL).
PDF adjunto o embebido con varias paginas: se parte en **una peticion Gemini por pagina** (cada pagina = como maximo un pago / una fila).
Etiquetas Gmail MERCANTIL (A) / BNC (B) / BINANCE (C) / BNV (D) solo si el correo cumple al 100%: cada candidato imagen/PDF debe ser
plantilla A o B con fecha/monto/ref + cedula resuelta, o plantilla C con monto/ref + cedula resuelta;
fecha de C = fecha del correo; cedula = lookup en tabla clientes por email De (From): primero `email`, luego `email_secundario`.
Si no hay cliente para ese email: columna Cedula = ERROR EMAIL y en Gmail etiqueta **ERROR EMAIL**; si el comprobante es plantilla A/B/C/D reconocida,
tambien se aplican en el mismo hilo las etiquetas de plantilla (**MERCANTIL** / **BNC** / **BINANCE** / **BNV**) que correspondan a los archivos subidos a Drive (rotulacion conjunta).
Si falla la consulta a clientes: ERROR BD (misma etiqueta Gmail que ERROR EMAIL).
En ambos casos (3.3) igual se genera fila Excel y subida Drive si el comprobante es plantilla valida.
Si ninguna etiqueta de clasificacion aplica (MERCANTIL/BNC/BINANCE/BNV/MASTER/ERROR EMAIL): etiqueta Gmail **OTROS** (con candidatos imagen/PDF).
Si en cualquier archivo falta requisito o no es plantilla valida: no etiquetas de plantilla; con candidatos imagen/PDF
se marca **no leido** en Gmail para reintento (no se modifican estrellas: las deja el usuario). No inventar datos: Gemini ya devuelve NA si no hay certeza.
Excel: GET /pagos/gmail/download-excel.
Cedula: por defecto solo desde tabla clientes por email del De (From): `email` y `email_secundario`; nunca desde la imagen.
Excepcion: scan_filter **error_email_rescan** (correos con etiqueta ERROR EMAIL sin EMAIL-12) — plantillas **A** y **B**: cedula se lee de la imagen (Gemini) o columna **ERROR** si no es clara; ademas etiqueta Gmail **EMAIL-12** si hubo fila A/B confirmada.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import (
    build_drive_service,
    get_or_create_folder,
    upload_file,
)
from app.services.pagos_gmail.gmail_service import (
    add_message_user_labels_only,
    build_gmail_service,
    ensure_user_label_id,
    get_pagos_gmail_image_pdf_files_for_pipeline,
    get_message_date,
    get_message_full_payload,
    get_message_raw_bytes,
    get_or_create_pagos_gmail_plantilla_label_ids,
    list_messages_by_filter,
    mark_as_read,
    mark_message_unread,
    PagosGmailGmailListError,
    PAGOS_GMAIL_LABEL_EMAIL_12,
    PAGOS_GMAIL_LABEL_ERROR_EMAIL,
    PAGOS_GMAIL_LABEL_OTROS,
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
    get_folder_name_from_date,
    get_sheet_name_for_date,
    normalizar_fecha_pago,
    normalizar_referencia,
    resolve_banco_para_excel_pagos_gmail,
)

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
    Si no hay fila: ERROR EMAIL. Si falla la consulta: ERROR BD. (3.3 sigue generando fila Excel/Drive.)
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
    Ejecuta el pipeline Gmail -> Gemini -> (Drive+BD si plantilla 1/2/3/4 y datos completos).
    Por adjunto OK (y remitente en clientes para cedula): etiqueta IMAGEN 1 (A), 2 (B), 3 (C) o 4 (D); cierre: leido si hubo digitalizacion 100%% OK.
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (por defecto API/UI: all).
      Por defecto (**all** / **pending_identification**): inbox con imagen/PDF — leidos y no leidos (el pipeline no modifica estrellas Gmail),
      con cualquier etiqueta de usuario (incluye **ERROR EMAIL**; la consulta Gmail no excluye esa etiqueta).
      **unread** / **read**: mismo criterio base + ``is:unread`` / ``is:read`` en la búsqueda Gmail.
      **error_email_rescan**: solo hilos con etiqueta **ERROR EMAIL** y sin **EMAIL-12**; Gemini en modo Mercantil/BNC con cédula en imagen para A/B.
      pending_identification es alias del listado base (nombre conservado para scheduler/API).
    Orden comprobantes OK: insert pagos_gmail_sync_item + gmail_temporal (sin Drive) -> commit -> subida Drive -> commit enlaces.
    Los mensajes de cada lote se ordenan por fecha del correo de mas antiguo a mas reciente antes de procesar.
    Una sola pasada de listado+proceso por ejecucion (salvo reintentos manuales).
    Tras listar **todos** los mensajes que cumplen el filtro (paginacion completa), se ordenan siempre del **mas antiguo al mas reciente**
    y se procesan en ese orden estricto (primer correo de la lista primero, ultimo al final).
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

    logger.info("[PAGOS_GMAIL] Credenciales OK; construyendo servicios Google")
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    logger.info("[PAGOS_GMAIL] Servicios Drive/Gmail construidos (Sheets eliminado)")

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
    drive_errors = 0
    # Correos con digitalizacion 100%% y etiquetas de plantilla aplicadas + marcados leidos en Gmail.
    correos_marcados_revision = 0
    plantilla_label_cache: Dict[str, Optional[str]] = {}
    error_email_rescan = (scan_filter or "").strip().lower() == "error_email_rescan"

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
            nonlocal emails_ok, files_ok, drive_errors, correos_marcados_revision
            if batch:
                    logger.info(
                    "[PAGOS_GMAIL] Procesando lote %s: %d correos (imagen/PDF pipeline, formatos A/B/C/D)",
                    label,
                    len(batch),
                )
            for msg_info in batch:
                msg_id = msg_info["id"]
                committed_ab_error_email_rescan = False
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
                    continue
                remitente_solo_master = sender_lc == PAGOS_GMAIL_SENDER_MASTER
                subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
                msg_date = get_message_date(headers)
                sheet_name = get_sheet_name_for_date(msg_date)
                folder_name = get_folder_name_from_date(msg_date)

                logger.info(
                    "[PAGOS_GMAIL] -- Correo %d (%s) id=%s | de=%s | asunto=%s",
                    emails_ok + 1,
                    label,
                    msg_id,
                    sender[:40],
                    subject[:50],
                )

                folder_id = get_or_create_folder(drive_svc, folder_name)
                if not folder_id:
                    drive_errors += 1
                    logger.warning(
                        "[PAGOS_GMAIL] No se pudo crear carpeta Drive '%s' - omitiendo msg %s",
                        folder_name,
                        msg_id,
                    )
                    continue

                logger.info("[PAGOS_GMAIL]   folder_id=%s", folder_id)

                full_payload = get_message_full_payload(gmail_svc, msg_id)
                if not full_payload and payload.get("parts"):
                    full_payload = payload

                drive_email_link: Optional[str] = None
                raw_eml = get_message_raw_bytes(gmail_svc, msg_id)
                if not raw_eml:
                    logger.warning(
                        "[PAGOS_GMAIL]   Email .eml no obtenido (msg_id=%s) - columna Ver email vacia",
                        msg_id,
                    )
                # .eml a Drive solo despues del primer commit de filas de comprobante (misma carpeta).

                attachments = get_pagos_gmail_image_pdf_files_for_pipeline(
                    gmail_svc, msg_id, full_payload or {}
                )
                candidatos = expand_pipeline_pdf_tuples(attachments)

                logger.info(
                    "[PAGOS_GMAIL]   candidatos imagen/PDF (adjunto + embebido + reenvio, dedup; PDF multi-pag -> N): %d - %s",
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
                gmail_etiqueta_clasificacion_aplicada = False
                if not candidatos:
                    any_incomplete_or_skipped = True

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
                for filename, content, mime_type, origen_binario in candidatos:
                    try:
                        fmt, data = classify_and_extract_pagos_gmail_attachment(
                            content,
                            filename,
                            remitente_correo_header=from_h,
                            origen_binario=origen_binario,
                            modo_error_email_ab=error_email_rescan,
                        )

                        if fmt not in PAGOS_GMAIL_FORMATOS_PLANTILLA:
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.warning(
                                "[PAGOS_GMAIL]   No es plantilla A/B/C/D - no Drive/BD: %s",
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
                        elif error_email_rescan and fmt in ("A", "B"):
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
                                    "[PAGOS_GMAIL]   Formato NR pero fila incompleta (monto!=NR o cedula vacia) - no Drive/BD: %s",
                                    filename,
                                )
                                continue
                        elif not _campos_completos(f, c, m, r):
                            any_incomplete_or_skipped = True
                            any_skipped_not_plantilla_o_campos = True
                            logger.warning(
                                "[PAGOS_GMAIL]   Plantilla %s pero columnas incompletas - no Drive/BD: %s",
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
                            db.commit()
                            committed_comprobante_rows = True
                            for _, _, p in rows_pairs:
                                if error_email_rescan and p.get("fmt") in ("A", "B"):
                                    committed_ab_error_email_rescan = True
                                    break
                            logger.info(
                                "[PAGOS_GMAIL]   Commit BD inicial: %d fila(s) comprobante sin enlaces Drive aun",
                                len(rows_pairs),
                            )
                        except Exception as commit_err:
                            logger.warning(
                                "[PAGOS_GMAIL] Error commit filas BD (antes de Drive): %s",
                                commit_err,
                            )
                            db.rollback()
                            any_incomplete_or_skipped = True
                            rows_pairs = []
                        else:
                            if raw_eml:
                                eml_name = f"email_{msg_id}.eml"
                                up_eml = upload_file(
                                    drive_svc,
                                    MediaIoBaseUpload,
                                    folder_id,
                                    eml_name,
                                    raw_eml,
                                    "message/rfc822",
                                )
                                if up_eml:
                                    _, drive_email_link = up_eml
                                    logger.info(
                                        "[PAGOS_GMAIL]   Email guardado en Drive: %s",
                                        eml_name,
                                    )
                                else:
                                    logger.warning(
                                        "[PAGOS_GMAIL]   Email .eml no subido (msg_id=%s)",
                                        msg_id,
                                    )

                            for si, gt, p in rows_pairs:
                                up = upload_file(
                                    drive_svc,
                                    MediaIoBaseUpload,
                                    folder_id,
                                    p["filename"],
                                    p["content"],
                                    p["mime_type"],
                                )
                                if not up:
                                    any_incomplete_or_skipped = True
                                    logger.warning(
                                        "[PAGOS_GMAIL]   Drive fallo subida tras commit BD - fila sin link: %s",
                                        p["filename"],
                                    )
                                    continue
                                file_id, drive_link = up
                                logger.info(
                                    "[PAGOS_GMAIL]   Drive OK: %s -> %s",
                                    p["filename"],
                                    (drive_link or "")[:60],
                                )
                                si.drive_file_id = file_id
                                si.drive_link = drive_link or None
                                si.drive_email_link = drive_email_link
                                gt.drive_file_id = file_id
                                gt.drive_link = drive_link or None
                                gt.drive_email_link = drive_email_link
                                files_ok += 1
                                had_complete_digitalization = True
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
                                if label_id and not remitente_solo_master:
                                    label_ids_for_message.append(label_id)
                                logger.info(
                                    "[PAGOS_GMAIL]   Digitalizado OK (%s); etiquetas plantilla solo si 100%% candidatos: %s",
                                    etiqueta_nombre,
                                    p["filename"],
                                )

                            try:
                                db.commit()
                            except Exception as upd_err:
                                logger.warning(
                                    "[PAGOS_GMAIL] Error commit enlaces Drive en BD: %s",
                                    upd_err,
                                )
                                db.rollback()
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
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; comprobantes reconocidos y subidos pero "
                            "remitente sin match en clientes (columna Cedula ERROR EMAIL/BD). "
                            "En Gmail se aplicaran conjuntamente ERROR EMAIL y etiquetas de plantilla por archivo OK.",
                            n_att,
                        )
                    elif any_skipped_not_plantilla_o_campos:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; uno o mas no son plantilla A/B/C/D valida "
                            "o fallaron -> sin etiquetas plantilla ni leido (se exige 100%% OK en todos). "
                            "Puede haber filas BD sin link Drive si fallo la subida tras el primer commit.",
                            n_att,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Resumen correo: %d adjuntos; incompleto por commit/subida Drive u otro fallo "
                            "-> sin etiquetas plantilla ni leido (100%% en todos).",
                            n_att,
                        )

                fully_digitized_email = (
                    len(candidatos) > 0
                    and not any_incomplete_or_skipped
                    and had_complete_digitalization
                )
                plantilla_unique_ids = list(
                    dict.fromkeys(x for x in label_ids_for_message if x)
                )
                # Precursores (ERROR EMAIL / EMAIL-12): se combinan con etiquetas de plantilla en una sola llamada
                # a Gmail cuando apliquen varias a la vez (rotulacion conjunta).
                gmail_label_id_error_email: Optional[str] = None
                gmail_label_id_email_12: Optional[str] = None
                if (
                    any_cedula_lookup_failed
                    and committed_comprobante_rows
                    and not remitente_solo_master
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
                            "[PAGOS_GMAIL]   Gmail: se aplicara etiqueta %s (remitente sin match en clientes o ERROR BD)",
                            k_err,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s — revisar permisos Gmail",
                            k_err,
                        )

                if (
                    error_email_rescan
                    and committed_ab_error_email_rescan
                    and committed_comprobante_rows
                    and not remitente_solo_master
                ):
                    k12 = PAGOS_GMAIL_LABEL_EMAIL_12
                    if k12 not in plantilla_label_cache:
                        plantilla_label_cache[k12] = ensure_user_label_id(gmail_svc, k12)
                    lid12 = plantilla_label_cache.get(k12)
                    if lid12:
                        gmail_label_id_email_12 = lid12
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: se aplicara etiqueta %s (re-scan ERROR EMAIL, fila Mercantil/BNC)",
                            k12,
                        )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k12,
                        )

                gmail_precursor_label_ids = list(
                    dict.fromkeys(
                        x
                        for x in (gmail_label_id_error_email, gmail_label_id_email_12)
                        if x
                    )
                )

                if remitente_solo_master and candidatos:
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
                                    [*gmail_precursor_label_ids, id_master]
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
                            add_message_user_labels_only(
                                gmail_svc, msg_id, [id_master]
                            )
                            gmail_etiqueta_clasificacion_aplicada = True
                            logger.info(
                                "[PAGOS_GMAIL]   Gmail: %s — solo %s (sin MERCANTIL / BNC / BINANCE / BNV / ERROR EMAIL)",
                                PAGOS_GMAIL_SENDER_MASTER,
                                k_master,
                            )
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Gmail: no se pudo crear/obtener etiqueta %s",
                            k_master,
                        )
                elif fully_digitized_email:
                    batch_ok = list(
                        dict.fromkeys([*gmail_precursor_label_ids, *plantilla_unique_ids])
                    )
                    if batch_ok:
                        add_message_user_labels_only(gmail_svc, msg_id, batch_ok)
                    gmail_etiqueta_clasificacion_aplicada = True
                    mark_as_read(gmail_svc, msg_id)
                    correos_marcados_revision += 1
                    logger.info(
                        "[PAGOS_GMAIL]   Gmail: 100%% adjuntos OK — etiquetas usuario aplicadas: %d id(s) (precursor + plantilla); leido",
                        len(batch_ok),
                    )
                elif (
                    committed_comprobante_rows
                    and not remitente_solo_master
                    and (gmail_precursor_label_ids or plantilla_unique_ids)
                ):
                    batch_partial = list(
                        dict.fromkeys(
                            [*gmail_precursor_label_ids, *plantilla_unique_ids]
                        )
                    )
                    if batch_partial:
                        add_message_user_labels_only(
                            gmail_svc, msg_id, batch_partial
                        )
                        gmail_etiqueta_clasificacion_aplicada = True
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: etiquetas usuario aplicadas conjuntamente: %d id(s) "
                            "(ERROR EMAIL/EMAIL-12 si aplica + MERCANTIL/BNC/BINANCE/BNV por comprobante subido)",
                            len(batch_partial),
                        )
                    if candidatos:
                        mark_message_unread(gmail_svc, msg_id)
                        logger.info(
                            "[PAGOS_GMAIL]   Gmail: hilo NO LEIDO (revision; no 100%% digitalizacion completa; "
                            "estrellas Gmail no se modifican)"
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

                if candidatos and not gmail_etiqueta_clasificacion_aplicada:
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
        if not messages:
            logger.info("[PAGOS_GMAIL] No hay correos con filtro %s", scan_filter)
        else:
            process_message_batch(messages, "run")

        sync.finished_at = datetime.now(timezone.utc)
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        logger.info("[PAGOS_GMAIL] FIN pipeline: emails=%d filas=%d drive_errors=%d",
            emails_ok, files_ok, drive_errors)

        if drive_errors > 0 and emails_ok == 0:
            sync.status = "error"
            sync.error_message = (
                f"Fallo Drive en {drive_errors} correo(s): no se pudo crear carpeta. "
                "Verifica permisos de la cuenta de servicio en Google Drive."
            )
        else:
            sync.status = "success"
            if drive_errors > 0:
                logger.warning("[PAGOS_GMAIL] %d correos omitidos por fallo Drive; %d procesados OK", drive_errors, emails_ok)
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
        db.commit()
        return sync_id, "error"
