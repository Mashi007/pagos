"""
OrquestaciÃ³n: Gmail -> Drive (imÃ¡genes) -> Gemini (extracciÃ³n) -> BD (PostgreSQL).
Google Sheets eliminado: el Excel se genera directamente desde la BD.
Regla Ãºnica de inclusiÃ³n: CORREO NO LEÃDO. No se restringe el escaneo por asunto, remitente
ni por tener adjuntos; todos los mensajes con label UNREAD se procesan. Si un correo se
re-marca como no leÃ­do (p. ej. correcciÃ³n), se procesarÃ¡ de nuevo en la siguiente ejecuciÃ³n.

Flujo por correo (en orden):
  1. Listar no leÃ­dos en Gmail
  2. Por cada correo en orden: obtener payload completo, extraer imÃ¡genes/PDFs
  3. Subir cada imagen a Drive (carpeta por fecha)
  4. Enviar imagen a Gemini â†’ extraer fecha_pago, cedula, monto, numero_referencia
  5. Guardar fila en BD (PagosGmailSyncItem) â€” commit incremental por correo
  6. Marcar correo como leÃ­do
  7. Al terminar el lote: ciclo de revisiÃ³n (hasta 10 pasadas): volver a listar no leÃ­dos; si hay alguno, procesarlos; repetir hasta que no quede ninguno o 10 pasadas.
El Excel se descarga vÃ­a GET /pagos/gmail/download-excel (generado desde BD).

Regla de filas: 1 imagen/adjunto de un correo = 1 fila en BD (PagosGmailSyncItem) = 1 pago en el Excel.
Ejemplo: un email con 3 imÃ¡genes genera 3 filas (3 pagos). Sin imÃ¡genes: 1 fila por correo (datos de asunto/cuerpo o NA).
"""
import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
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
    scan_filter: "unread" | "read" | "all" â€” quÃ© correos listar. Solo con "unread" se marcan como leÃ­dos y se hace ciclo de revisiÃ³n.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    logger.warning("[PAGOS_GMAIL] â–¶ INICIO pipeline (existing_sync_id=%s, scan_filter=%s)", existing_sync_id, scan_filter)
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
        logger.warning("[PAGOS_GMAIL] âœ— Sin credenciales â€” pipeline abortado")
        return existing_sync_id, "no_credentials"

    logger.warning("[PAGOS_GMAIL] âœ“ Credenciales OK â€” construyendo servicios Google")
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    logger.warning("[PAGOS_GMAIL] âœ“ Servicios Drive/Gmail construidos (Sheets eliminado)")

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
        logger.warning("[PAGOS_GMAIL] â†’ Listando correos (filtro=%s)...", scan_filter)
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
            logger.warning("[PAGOS_GMAIL] â„¹ Duplicados eliminados: %d â†’ %d mensajes Ãºnicos", len(raw_messages), len(messages))
        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total = len(messages)
        # Con "unread" o "all" procesamos todos (sin límite); "unread" además hace vueltas hasta completar.
        if scan_filter in ("all", "unread"):
            max_emails = 0
        logger.warning("[PAGOS_GMAIL] âœ“ Correos (filtro=%s): %d (mÃ¡x por ejecuciÃ³n: %s)", scan_filter, total, max_emails or "sin lÃ­mite")
        if total == 0:
            logger.warning("[PAGOS_GMAIL] â„¹ No hay correos con filtro %s â€” pipeline termina", scan_filter)
        if max_emails and max_emails > 0 and total > max_emails:
            messages = messages[:max_emails]
            logger.warning("[PAGOS_GMAIL] â„¹ Limitado a %d correos (de %d)", max_emails, total)

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
                # Ãšnico criterio: correo no leÃ­do (se procesan todos; sin filtro por asunto/remitente)
                msg_date = get_message_date(headers)
                sheet_name = get_sheet_name_for_date(msg_date)
                folder_name = get_folder_name_from_date(msg_date)

                logger.warning("[PAGOS_GMAIL] â”€â”€ Correo %d (%s) id=%s | de=%s | asunto=%s",
                    emails_ok + 1, label, msg_id, sender[:40], subject[:50])

                folder_id = get_or_create_folder(drive_svc, folder_name)
                if not folder_id:
                    drive_errors += 1
                    logger.warning("[PAGOS_GMAIL] âœ— No se pudo crear carpeta Drive '%s' â€” omitiendo msg %s", folder_name, msg_id)
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
                    logger.warning("[PAGOS_GMAIL]   Fwd detectado â†’ correo_origen=%s", sender[:60])

                body_text = get_message_body_text(full_payload) if full_payload else ""
                if body_text:
                    logger.warning("[PAGOS_GMAIL]   Cuerpo correo: %d caracteres para contexto Gemini", len(body_text))

                drive_email_link: Optional[str] = None
                raw_eml = get_message_raw_bytes(gmail_svc, msg_id)
                if not raw_eml:
                    logger.warning("[PAGOS_GMAIL]   Email .eml no obtenido (msg_id=%s) â€” columna Â«Ver emailÂ» quedarÃ¡ vacÃ­a", msg_id)
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
                        logger.warning("[PAGOS_GMAIL]   Email .eml no subido a Drive (msg_id=%s) â€” columna Â«Ver emailÂ» quedarÃ¡ vacÃ­a", msg_id)

                attachments = get_all_images_and_files_for_message(gmail_svc, msg_id, full_payload)
                logger.warning("[PAGOS_GMAIL]   imÃ¡genes encontradas: %d â€” %s",
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
                        db.add(GmailTemporal(
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
                        logger.warning("[PAGOS_GMAIL]   Sin imÃ¡genes â†’ datos extraÃ­dos de asunto/cuerpo del correo")
                    else:
                        _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, email_lnk=drive_email_link)
                        logger.warning("[PAGOS_GMAIL]   Sin imÃ¡genes ni asunto/cuerpo â†’ fila NA guardada")
                else:
                    # Regla: 1 imagen = 1 fila en BD = 1 pago en el Excel. Ej.: email con 3 imÃ¡genes â†’ 3 filas (3 pagos).
                    for filename, content, mime_type in attachments:
                        try:
                            up = upload_file(drive_svc, MediaIoBaseUpload, folder_id, filename, content, mime_type)
                            file_id = None
                            drive_link = ""
                            if up:
                                file_id, drive_link = up
                                logger.warning("[PAGOS_GMAIL]   Drive OK: %s â†’ %s", filename, drive_link[:60])

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
                    logger.warning("[PAGOS_GMAIL]   âœ— Sin fila guardada para %s â€” fila NA de respaldo", msg_id)
                    _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, email_lnk=drive_email_link)

                if scan_filter == "unread":
                    mark_as_read(gmail_svc, msg_id)
                    if not mensaje_tiene_fila_valida:
                        logger.warning("[PAGOS_GMAIL]   Correo marcado leÃ­do (todo NA)")
                emails_ok += 1

                sync.emails_processed = emails_ok
                sync.files_processed = files_ok
                db.commit()

        # Con "unread": bucle que llega al final de la bandeja y vuelve al inicio hasta vuelta completa (0 sin leer).
        if scan_filter == "unread":
            vuelta_num = 0
            max_vueltas = 20
            while True:
                vuelta_num += 1
                logger.warning("[PAGOS_GMAIL] Listando no leidos desde inicio de bandeja (vuelta %d)...", vuelta_num)
                raw_messages = list_messages_by_filter(gmail_svc, "unread")
                seen_ids = set()
                messages = []
                for m in raw_messages:
                    mid = m["id"]
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    messages.append(m)
                if not messages:
                    logger.warning("[PAGOS_GMAIL] Vuelta completa: no quedan correos sin leer.")
                    break
                logger.warning("[PAGOS_GMAIL] Correos en esta vuelta: %d (procesando hasta el final de bandeja)", len(messages))
                process_message_batch(messages, "vuelta %d" % vuelta_num)
                if vuelta_num >= max_vueltas:
                    logger.warning("[PAGOS_GMAIL] Maximo de vueltas (%d) alcanzado.", max_vueltas)
                    break
        else:
            process_message_batch(messages, "inicial")

        # Fin del loop

        sync.finished_at = datetime.utcnow()
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        logger.warning("[PAGOS_GMAIL] â–  FIN pipeline: emails=%d filas=%d drive_errors=%d",
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
