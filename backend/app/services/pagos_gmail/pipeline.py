"""
Orquestacion: Gmail -> Gemini (solo imagen/PDF incrustados en cuerpo: inline, related, data: HTML) -> si formato A o B
  -> Drive + BD; si no cumple plantillas 1/2 o faltan columnas -> no fila ni archivo en Drive para ese adjunto.

Por cada adjunto digitalizado OK: etiqueta Gmail IMAGEN 1 (formato A) o IMAGEN 2 (formato B) + estrella.
Al cerrar el correo: leido si hubo al menos un OK; si no y filtro unread, sin estrella + no leido.
Excel: GET /pagos/gmail/download-excel.
"""
import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import (
    build_drive_service,
    get_or_create_folder,
    upload_file,
)
from app.services.pagos_gmail.gmail_service import (
    add_message_star_and_user_labels,
    build_gmail_service,
    get_body_embedded_image_pdf_files_for_message,
    get_message_date,
    get_message_full_payload,
    get_message_raw_bytes,
    get_or_create_pagos_gmail_plantilla_label_ids,
    list_messages_by_filter,
    mark_as_read,
    mark_unread_clear_star,
    PAGOS_GMAIL_LABEL_IMAGEN_1,
    PAGOS_GMAIL_LABEL_IMAGEN_2,
)
from app.services.pagos_gmail.gemini_service import (
    classify_and_extract_pagos_gmail_attachment,
    PAGOS_NA,
)
from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    formatear_cedula,
    get_folder_name_from_date,
    get_sheet_name_for_date,
    normalizar_fecha_pago,
    normalizar_referencia,
)

logger = logging.getLogger(__name__)


def run_pipeline(
    db: Session,
    existing_sync_id: Optional[int] = None,
    scan_filter: str = "unread",
) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline Gmail -> Gemini -> (Drive+BD solo si plantilla 1/2 y columnas completas).
    Por adjunto OK: etiqueta IMAGEN 1 (A) o IMAGEN 2 (B) + estrella; cierre: leido si hubo algun OK.
    scan_filter: "unread" | "read" | "all".
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    logger.warning("[PAGOS_GMAIL] INICIO pipeline (existing_sync_id=%s, scan_filter=%s)", existing_sync_id, scan_filter)
    creds = get_pagos_gmail_credentials()
    if not creds:
        if existing_sync_id:
            try:
                from sqlalchemy import select as sa_select
                sync_row = db.execute(sa_select(PagosGmailSync).where(PagosGmailSync.id == existing_sync_id)).scalars().first()
                if sync_row:
                    sync_row.status = "error"
                    sync_row.finished_at = datetime.utcnow()
                    sync_row.error_message = "no_credentials"
                    db.commit()
            except Exception:
                pass
        logger.warning("[PAGOS_GMAIL] Sin credenciales; pipeline abortado")
        return existing_sync_id, "no_credentials"

    logger.warning("[PAGOS_GMAIL] Credenciales OK; construyendo servicios Google")
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    logger.warning("[PAGOS_GMAIL] Servicios Drive/Gmail construidos (Sheets eliminado)")

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
    # Correos que quedaron con estrella tras digitalizacion completa (cuatro columnas).
    correos_marcados_revision = 0
    processed_msg_ids: set[str] = set()
    plantilla_label_cache: Dict[str, Optional[str]] = {}

    try:
        logger.warning("[PAGOS_GMAIL] Listando correos (filtro=%s)...", scan_filter)
        raw_messages = list_messages_by_filter(gmail_svc, scan_filter)
        seen_ids: set[str] = set()
        messages: list[dict] = []
        for m in raw_messages:
            mid = m["id"]
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            messages.append(m)
        if len(messages) < len(raw_messages):
            logger.warning(
                "[PAGOS_GMAIL] Duplicados eliminados: %d -> %d mensajes",
                len(raw_messages),
                len(messages),
            )
        logger.warning(
            "[PAGOS_GMAIL] Correos (filtro=%s): %d",
            scan_filter,
            len(messages),
        )
        if not messages:
            logger.warning("[PAGOS_GMAIL] No hay correos con filtro %s", scan_filter)

        def process_message_batch(batch: list[dict], label: str) -> None:
            nonlocal emails_ok, files_ok, drive_errors, correos_marcados_revision
            if batch:
                logger.warning(
                    "[PAGOS_GMAIL] Procesando lote %s: %d correos (imagen/PDF en cuerpo, formatos A/B)",
                    label,
                    len(batch),
                )
            for msg_info in batch:
                msg_id = msg_info["id"]
                payload = msg_info["payload"]
                headers = msg_info["headers"]
                from_h = headers.get("from") or headers.get("From") or ""
                sender = extract_sender_email(from_h)
                subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
                msg_date = get_message_date(headers)
                sheet_name = get_sheet_name_for_date(msg_date)
                folder_name = get_folder_name_from_date(msg_date)

                logger.warning(
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
                        "[PAGOS_GMAIL] No se pudo crear carpeta Drive '%s' — omitiendo msg %s",
                        folder_name,
                        msg_id,
                    )
                    continue

                processed_msg_ids.add(msg_id)

                logger.warning("[PAGOS_GMAIL]   folder_id=%s", folder_id)

                full_payload = get_message_full_payload(gmail_svc, msg_id)
                if not full_payload and payload.get("parts"):
                    full_payload = payload

                drive_email_link: Optional[str] = None
                raw_eml = get_message_raw_bytes(gmail_svc, msg_id)
                if not raw_eml:
                    logger.warning(
                        "[PAGOS_GMAIL]   Email .eml no obtenido (msg_id=%s) — columna Ver email vacia",
                        msg_id,
                    )
                else:
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
                        logger.warning("[PAGOS_GMAIL]   Email guardado en Drive: %s", eml_name)
                    else:
                        logger.warning(
                            "[PAGOS_GMAIL]   Email .eml no subido (msg_id=%s)",
                            msg_id,
                        )

                attachments = get_body_embedded_image_pdf_files_for_message(
                    gmail_svc, msg_id, full_payload or {}
                )

                logger.warning(
                    "[PAGOS_GMAIL]   imagen/PDF en cuerpo: %d — %s",
                    len(attachments),
                    ", ".join(f"{f}({len(c)}B)" for f, c, _ in attachments)
                    if attachments
                    else "ninguno",
                )

                had_complete_digitalization = False
                any_incomplete_or_skipped = False
                if not attachments:
                    any_incomplete_or_skipped = True

                def _campos_completos(fecha: str, cedula: str, monto: str, ref: str) -> bool:
                    def ok(val: str) -> bool:
                        s = (val or "").strip()
                        return bool(s) and s.upper() != PAGOS_NA

                    return ok(fecha) and ok(cedula) and ok(monto) and ok(ref)

                def _guardar_en_bd(
                    correo: str,
                    fecha: str,
                    cedula: str,
                    monto: str,
                    referencia: str,
                    drive_file_id=None,
                    drive_lnk="",
                    email_lnk: Optional[str] = None,
                ) -> bool:
                    nonlocal files_ok
                    try:
                        db.add(
                            PagosGmailSyncItem(
                                sync_id=sync_id,
                                correo_origen=correo,
                                asunto=subject,
                                fecha_pago=fecha,
                                cedula=cedula,
                                monto=monto,
                                numero_referencia=referencia,
                                drive_file_id=drive_file_id,
                                drive_link=drive_lnk or None,
                                drive_email_link=email_lnk or None,
                                sheet_name=sheet_name,
                            )
                        )
                        db.add(
                            GmailTemporal(
                                correo_origen=correo,
                                asunto=subject,
                                fecha_pago=fecha,
                                cedula=cedula,
                                monto=monto,
                                numero_referencia=referencia,
                                drive_file_id=drive_file_id,
                                drive_link=drive_lnk or None,
                                drive_email_link=email_lnk or None,
                                sheet_name=sheet_name,
                            )
                        )
                        files_ok += 1
                        return True
                    except Exception as db_err:
                        logger.warning("[PAGOS_GMAIL] Error guardando en BD: %s", db_err)
                        return False

                def _v(x: Optional[str]) -> str:
                    v = (x or "").strip()
                    return v if v and v.upper() != "NA" else ""

                for filename, content, mime_type in attachments:
                    try:
                        fmt, data = classify_and_extract_pagos_gmail_attachment(
                            content, filename
                        )

                        if fmt == "ninguno":
                            any_incomplete_or_skipped = True
                            logger.warning(
                                "[PAGOS_GMAIL]   No coincide plantilla 1/2 — no Drive/BD: %s",
                                filename,
                            )
                            continue

                        f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                        c = formatear_cedula(_v(data.get("cedula")))
                        m = _v(data.get("monto"))
                        r = normalizar_referencia(_v(data.get("numero_referencia")))
                        if not _campos_completos(f, c, m, r):
                            any_incomplete_or_skipped = True
                            logger.warning(
                                "[PAGOS_GMAIL]   Formato %s pero columnas incompletas — no Drive/BD: %s",
                                fmt,
                                filename,
                            )
                            continue

                        up = upload_file(
                            drive_svc,
                            MediaIoBaseUpload,
                            folder_id,
                            filename,
                            content,
                            mime_type,
                        )
                        file_id = None
                        drive_link = ""
                        if up:
                            file_id, drive_link = up
                            logger.warning(
                                "[PAGOS_GMAIL]   Drive OK: %s -> %s",
                                filename,
                                drive_link[:60],
                            )
                        else:
                            logger.warning(
                                "[PAGOS_GMAIL]   Drive fallo subida — no fila BD: %s",
                                filename,
                            )
                            any_incomplete_or_skipped = True
                            continue

                        ok_db = _guardar_en_bd(
                            sender,
                            f,
                            c,
                            m,
                            r,
                            drive_file_id=file_id,
                            drive_lnk=drive_link or "",
                            email_lnk=drive_email_link,
                        )
                        if ok_db:
                            had_complete_digitalization = True
                            id_a, id_b = get_or_create_pagos_gmail_plantilla_label_ids(
                                gmail_svc, plantilla_label_cache
                            )
                            label_id = id_a if fmt == "A" else id_b
                            add_message_star_and_user_labels(
                                gmail_svc,
                                msg_id,
                                [label_id] if label_id else [],
                            )
                            etiqueta_nombre = (
                                PAGOS_GMAIL_LABEL_IMAGEN_1
                                if fmt == "A"
                                else PAGOS_GMAIL_LABEL_IMAGEN_2
                            )
                            logger.warning(
                                "[PAGOS_GMAIL]   Gmail: estrella + etiqueta %s (%s)",
                                etiqueta_nombre,
                                filename,
                            )
                        else:
                            any_incomplete_or_skipped = True
                    except Exception as e:
                        logger.warning("[PAGOS_GMAIL]   Error procesando %s: %s", filename, e)
                        any_incomplete_or_skipped = True

                if had_complete_digitalization:
                    mark_as_read(gmail_svc, msg_id)
                    if scan_filter == "unread":
                        correos_marcados_revision += 1
                    logger.warning(
                        "[PAGOS_GMAIL]   Gmail: leido (al menos un adjunto digitalizado; estrella/etiqueta por archivo)"
                    )
                elif scan_filter == "unread":
                    mark_unread_clear_star(gmail_svc, msg_id)
                    logger.warning(
                        "[PAGOS_GMAIL]   Gmail: sin estrella + no leido (ningun adjunto digitalizado)"
                    )

                emails_ok += 1

                sync.emails_processed = emails_ok
                sync.files_processed = files_ok
                db.commit()

        process_message_batch(messages, "run")

        if scan_filter == "unread" and messages:
            raw_b = list_messages_by_filter(gmail_svc, "unread")
            seen_b: set[str] = set()
            messages_b: list[dict] = []
            for m in raw_b:
                mid = m["id"]
                if mid in seen_b:
                    continue
                seen_b.add(mid)
                if mid not in processed_msg_ids:
                    messages_b.append(m)
            if messages_b:
                logger.warning(
                    "[PAGOS_GMAIL] Segunda pasada (no leidos no vistos en 1a): %d",
                    len(messages_b),
                )
                process_message_batch(messages_b, "repaso")

        sync.finished_at = datetime.utcnow()
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        logger.warning("[PAGOS_GMAIL] FIN pipeline: emails=%d filas=%d drive_errors=%d",
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

    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Pipeline error inesperado: %s", e)
        sync.finished_at = datetime.utcnow()
        sync.status = "error"
        sync.error_message = str(e)[:2000]
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        sync.correos_marcados_revision = correos_marcados_revision
        db.commit()
        return sync_id, "error"
