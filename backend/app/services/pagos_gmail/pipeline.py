"""
Orquestación: Gmail -> Drive (imágenes) -> Gemini (extracción) -> BD (PostgreSQL).
Google Sheets eliminado: el Excel se genera directamente desde la BD.
Regla única de inclusión: CORREO NO LEÍDO. No se restringe el escaneo por asunto, remitente
ni por tener adjuntos; todos los mensajes con label UNREAD se procesan. Si un correo se
re-marca como no leído (p. ej. corrección), se procesará de nuevo en la siguiente ejecución.

Flujo por correo (en orden):
  1. Listar no leídos en Gmail
  2. Por cada correo en orden: obtener payload completo, extraer imágenes/PDFs
  3. Subir cada imagen a Drive (carpeta por fecha)
  4. Enviar imagen a Gemini → extraer fecha_pago, cedula, monto, numero_referencia
  5. Guardar fila en BD (PagosGmailSyncItem) — commit incremental por correo
  6. Marcar correo como leído
  7. Al terminar el lote: ciclo de revisión (hasta 10 pasadas): volver a listar no leídos; si hay alguno, procesarlos; repetir hasta que no quede ninguno o 10 pasadas.
El Excel se descarga vía GET /pagos/gmail/download-excel (generado desde BD).

Regla de filas: 1 imagen/adjunto de un correo = 1 fila en BD (PagosGmailSyncItem) = 1 pago en el Excel.
Ejemplo: un email con 3 imágenes genera 3 filas (3 pagos). Sin imágenes: 1 fila por correo (datos de asunto/cuerpo o NA).
"""
import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import (
    build_drive_service,
    get_or_create_folder,
    upload_file,
)
from app.services.pagos_gmail.gmail_service import (
    build_gmail_service,
    extract_forwarded_sender,
    get_all_images_and_files_for_message,
    get_message_body_text,
    get_message_date,
    get_message_full_payload,
    get_message_raw_bytes,
    list_messages_by_filter,
    mark_as_read,
)
from app.services.pagos_gmail.gemini_service import extract_payment_data, PAGOS_NA
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
    Ejecuta el pipeline Gmail -> Drive -> Gemini -> BD.
    scan_filter: "unread" | "read" | "all" — qué correos listar. Solo con "unread" se marcan como leídos y se hace ciclo de revisión.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    logger.warning("[PAGOS_GMAIL] ▶ INICIO pipeline (existing_sync_id=%s, scan_filter=%s)", existing_sync_id, scan_filter)
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
        logger.warning("[PAGOS_GMAIL] ✗ Sin credenciales — pipeline abortado")
        return existing_sync_id, "no_credentials"

    logger.warning("[PAGOS_GMAIL] ✓ Credenciales OK — construyendo servicios Google")
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    logger.warning("[PAGOS_GMAIL] ✓ Servicios Drive/Gmail construidos (Sheets eliminado)")

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

    try:
        logger.warning("[PAGOS_GMAIL] → Listando correos (filtro=%s)...", scan_filter)
        raw_messages = list_messages_by_filter(gmail_svc, scan_filter)
        # Evitar procesar el mismo mensaje dos veces (Gmail API o listado puede devolver duplicados)
        seen_ids: set[str] = set()
        messages = []
        for m in raw_messages:
            mid = m["id"]
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            messages.append(m)
        if len(messages) < len(raw_messages):
            logger.warning("[PAGOS_GMAIL] ℹ Duplicados eliminados: %d → %d mensajes únicos", len(raw_messages), len(messages))
        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total = len(messages)
        logger.warning("[PAGOS_GMAIL] ✓ Correos (filtro=%s): %d (máx por ejecución: %s)", scan_filter, total, max_emails or "sin límite")
        if total == 0:
            logger.warning("[PAGOS_GMAIL] ℹ No hay correos con filtro %s — pipeline termina", scan_filter)
        if max_emails and max_emails > 0 and total > max_emails:
            messages = messages[:max_emails]
            logger.warning("[PAGOS_GMAIL] ℹ Limitado a %d correos (de %d)", max_emails, total)

        delay_gemini = getattr(settings, "PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS", 0) or 0

        def process_message_batch(batch: list[dict], label: str) -> None:
            nonlocal emails_ok, files_ok, drive_errors
            # Criterio unico: no leidos. No se filtra por asunto ni remitente; se procesan todos.
            if batch:
                logger.warning("[PAGOS_GMAIL] Procesando lote %s: %d correos (todos, sin filtro asunto/remitente)", label, len(batch))
            for msg_info in batch:
                msg_id = msg_info["id"]
                payload = msg_info["payload"]
                headers = msg_info["headers"]
                from_h = headers.get("from") or headers.get("From") or ""
                sender = extract_sender_email(from_h)
                subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
                # Único criterio: correo no leído (se procesan todos; sin filtro por asunto/remitente)
                msg_date = get_message_date(headers)
                sheet_name = get_sheet_name_for_date(msg_date)
                folder_name = get_folder_name_from_date(msg_date)

                logger.warning("[PAGOS_GMAIL] ── Correo %d (%s) id=%s | de=%s | asunto=%s",
                    emails_ok + 1, label, msg_id, sender[:40], subject[:50])

                folder_id = get_or_create_folder(drive_svc, folder_name)
                if not folder_id:
                    drive_errors += 1
                    logger.warning("[PAGOS_GMAIL] ✗ No se pudo crear carpeta Drive '%s' — omitiendo msg %s", folder_name, msg_id)
                    continue

                logger.warning("[PAGOS_GMAIL]   folder_id=%s", folder_id)

                full_payload = get_message_full_payload(gmail_svc, msg_id)
                if not full_payload and payload.get("parts"):
                    full_payload = payload

                forwarded_raw = extract_forwarded_sender(full_payload) if full_payload else None
                if forwarded_raw:
                    forwarded_email = extract_sender_email(forwarded_raw) or forwarded_raw
                    sender = forwarded_email
                    if "@" not in subject:
                        subject = forwarded_raw
                    logger.warning("[PAGOS_GMAIL]   Fwd detectado → correo_origen=%s", sender[:60])

                body_text = get_message_body_text(full_payload) if full_payload else ""
                if body_text:
                    logger.warning("[PAGOS_GMAIL]   Cuerpo correo: %d caracteres para contexto Gemini", len(body_text))

                drive_email_link: Optional[str] = None
                raw_eml = get_message_raw_bytes(gmail_svc, msg_id)
                if not raw_eml:
                    logger.warning("[PAGOS_GMAIL]   Email .eml no obtenido (msg_id=%s) — columna «Ver email» quedará vacía", msg_id)
                else:
                    eml_name = f"email_{msg_id}.eml"
                    up_eml = upload_file(
                        drive_svc, MediaIoBaseUpload, folder_id, eml_name,
                        raw_eml, "message/rfc822",
                    )
                    if up_eml:
                        _, drive_email_link = up_eml
                        logger.warning("[PAGOS_GMAIL]   Email guardado en Drive: %s", eml_name)
                    else:
                        logger.warning("[PAGOS_GMAIL]   Email .eml no subido a Drive (msg_id=%s) — columna «Ver email» quedará vacía", msg_id)

                attachments = get_all_images_and_files_for_message(gmail_svc, msg_id, full_payload)
                logger.warning("[PAGOS_GMAIL]   imágenes encontradas: %d — %s",
                    len(attachments),
                    ", ".join(f"{f}({len(c)}B)" for f, c, _ in attachments) if attachments else "ninguno")

                mensaje_tiene_fila_valida = False
                fila_guardada = False

                def _guardar_en_bd(correo: str, fecha: str, cedula: str, monto: str,
                                   referencia: str, drive_file_id=None, drive_lnk="",
                                   email_lnk: Optional[str] = None) -> bool:
                    nonlocal files_ok, fila_guardada
                    try:
                        db.add(PagosGmailSyncItem(
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
                        ))
                        files_ok += 1
                        fila_guardada = True
                        return True
                    except Exception as db_err:
                        logger.warning("[PAGOS_GMAIL] Error guardando en BD: %s", db_err)
                        return False

                def _v(x: Optional[str]) -> str:
                    v = (x or "").strip()
                    return v if v and v.upper() != "NA" else ""

                if len(attachments) == 0:
                    if (subject and subject.strip()) or (body_text and body_text.strip()):
                        data = extract_payment_data(subject=subject or None, body_text=body_text or None)
                        f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                        c = formatear_cedula(_v(data.get("cedula")))
                        m = _v(data.get("monto"))
                        r = normalizar_referencia(_v(data.get("numero_referencia")))
                        _guardar_en_bd(sender, f or PAGOS_NA, c or PAGOS_NA, m or PAGOS_NA, r or PAGOS_NA, email_lnk=drive_email_link)
                        logger.warning("[PAGOS_GMAIL]   Sin imágenes → datos extraídos de asunto/cuerpo del correo")
                    else:
                        _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, email_lnk=drive_email_link)
                        logger.warning("[PAGOS_GMAIL]   Sin imágenes ni asunto/cuerpo → fila NA guardada")
                else:
                    # Regla: 1 imagen = 1 fila en BD = 1 pago en el Excel. Ej.: email con 3 imágenes → 3 filas (3 pagos).
                    for filename, content, mime_type in attachments:
                        try:
                            up = upload_file(drive_svc, MediaIoBaseUpload, folder_id, filename, content, mime_type)
                            file_id = None
                            drive_link = ""
                            if up:
                                file_id, drive_link = up
                                logger.warning("[PAGOS_GMAIL]   Drive OK: %s → %s", filename, drive_link[:60])

                            data = extract_payment_data(
                                file_content=content,
                                filename=filename,
                                body_text=body_text or None,
                                subject=subject or None,
                            )
                            if delay_gemini > 0:
                                time.sleep(delay_gemini)

                            f = normalizar_fecha_pago(_v(data.get("fecha_pago")))
                            c = formatear_cedula(_v(data.get("cedula")))
                            m = _v(data.get("monto"))
                            r = normalizar_referencia(_v(data.get("numero_referencia")))
                            tiene_valido = bool(f or (c and c != PAGOS_NA) or m or r)
                            if tiene_valido:
                                mensaje_tiene_fila_valida = True

                            _guardar_en_bd(
                                sender,
                                f or PAGOS_NA, c or PAGOS_NA, m or PAGOS_NA, r or PAGOS_NA,
                                drive_file_id=file_id, drive_lnk=drive_link or "",
                                email_lnk=drive_email_link,
                            )
                        except Exception as e:
                            logger.warning("[PAGOS_GMAIL]   Error procesando %s: %s", filename, e)
                            _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, email_lnk=drive_email_link)

                if not fila_guardada:
                    logger.warning("[PAGOS_GMAIL]   ✗ Sin fila guardada para %s — fila NA de respaldo", msg_id)
                    _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, email_lnk=drive_email_link)

                if scan_filter == "unread":
                    mark_as_read(gmail_svc, msg_id)
                    if not mensaje_tiene_fila_valida:
                        logger.warning("[PAGOS_GMAIL]   Correo marcado leído (todo NA)")
                emails_ok += 1

                sync.emails_processed = emails_ok
                sync.files_processed = files_ok
                db.commit()

        process_message_batch(messages, "inicial")

        # Ciclo de revisión solo para "unread": volver a listar no leídos y procesar hasta que no quede ninguno (máx 10 pasadas)
        if scan_filter == "unread":
            max_revision_passes = 10
            for pass_num in range(1, max_revision_passes + 1):
                raw_again = list_messages_by_filter(gmail_svc, "unread")
                again_dedup = []
                seen_again = set()
                for m in raw_again:
                    if m["id"] in seen_again:
                        continue
                    seen_again.add(m["id"])
                    again_dedup.append(m)
                if not again_dedup:
                    if pass_num > 1:
                        logger.warning("[PAGOS_GMAIL] Ciclo revisión: no quedan no leídos - fin")
                    break
                if max_emails and max_emails > 0 and len(again_dedup) > max_emails:
                    again_dedup = again_dedup[:max_emails]
                logger.warning("[PAGOS_GMAIL] Ciclo revisión (pasada %d): %d correo(s) sin leer - procesando", pass_num, len(again_dedup))
                process_message_batch(again_dedup, "revisión pasada %d" % pass_num)

        # Fin del loop
        sync.finished_at = datetime.utcnow()
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        logger.warning("[PAGOS_GMAIL] ■ FIN pipeline: emails=%d filas=%d drive_errors=%d",
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
        db.commit()
        return sync_id, "error"
