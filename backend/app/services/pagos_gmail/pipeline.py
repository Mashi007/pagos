"""
Orquestación: Gmail -> Drive -> Gemini -> Sheets; marcar correo leído; registrar en BD (pagos_gmail_sync, pagos_gmail_sync_item).
Solo se procesan correos NO LEÍDOS: si un email fue leído no se volverá a revisar para digitalizar información.
Solo se procesan correos cuyo Asunto contiene una dirección de email; si no hay email en el Asunto se ignora el mensaje.
La información a extraer puede estar en adjuntos al email o en imágenes en el cuerpo (MIME inline o HTML base64).
Respeto de cuota Gemini: pausa entre llamadas (PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS) y opcional límite de correos por ejecución (PAGOS_GMAIL_MAX_EMAILS_PER_RUN).
"""
import logging
import time
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import (
    ROOT_FOLDER_ID,
    build_drive_service,
    get_or_create_folder,
    get_or_create_sheet_for_date,
    upload_file,
)
from app.services.pagos_gmail.gmail_service import (
    build_gmail_service,
    get_all_images_and_files_for_message,
    get_message_date,
    get_message_full_payload,
    list_unread_with_attachments,
    mark_as_read,
)
from app.services.pagos_gmail.gemini_service import extract_payment_data
from app.services.pagos_gmail.helpers import extract_sender_email, get_folder_name_from_date, get_sheet_name_for_date
from app.services.pagos_gmail.sheets_service import append_row

logger = logging.getLogger(__name__)


def run_pipeline(db: Session) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline completo. Crea registro en pagos_gmail_sync y items en pagos_gmail_sync_item.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    creds = get_pagos_gmail_credentials()
    if not creds:
        return None, "no_credentials"
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    from googleapiclient.discovery import build
    sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    sync_id = sync.id
    emails_ok = 0
    files_ok = 0
    try:
        messages = list_unread_with_attachments(gmail_svc)
        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total_unread = len(messages)
        if max_emails and max_emails > 0 and total_unread > max_emails:
            messages = messages[:max_emails]
            logger.info("[PAGOS_GMAIL] Limité a %d correos por ejecución (había %d no leídos; resto en próxima pasada)", max_emails, total_unread)
        delay_gemini = getattr(settings, "PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS", 0) or 0
        for msg_info in messages:
            msg_id = msg_info["id"]
            payload = msg_info["payload"]
            headers = msg_info["headers"]
            from_h = headers.get("from") or headers.get("From") or ""
            sender = extract_sender_email(from_h)
            subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
            msg_date = get_message_date(headers)
            folder_name = get_folder_name_from_date(msg_date)
            folder_id = get_or_create_folder(drive_svc, folder_name)
            if not folder_id:
                continue
            sheet_id = get_or_create_sheet_for_date(drive_svc, sheets_svc, msg_date)
            if not sheet_id:
                continue
            sheet_name = get_sheet_name_for_date(msg_date)
            full_payload = get_message_full_payload(gmail_svc, msg_id)
            if not full_payload and payload.get("parts"):
                full_payload = payload
            attachments = get_all_images_and_files_for_message(gmail_svc, msg_id, full_payload)
            if len(attachments) > 1:
                # Más de 1 adjunto: una sola fila con asunto en A y "varios archivos" en el resto; no Gemini ni Drive por archivo
                VARIOS = "varios archivos"
                row = [subject, VARIOS, VARIOS, VARIOS, VARIOS, ""]
                if append_row(sheets_svc, sheet_id, row):
                    item = PagosGmailSyncItem(
                        sync_id=sync_id,
                        correo_origen=sender,
                        asunto=subject,
                        fecha_pago=VARIOS,
                        cedula=VARIOS,
                        monto=VARIOS,
                        numero_referencia=VARIOS,
                        drive_file_id=None,
                        drive_link=None,
                        sheet_name=sheet_name,
                    )
                    db.add(item)
                    files_ok += 1
                logger.info("[PAGOS_GMAIL] Correo con %d adjuntos: fila única «varios archivos» (asunto en columna A)", len(attachments))
            else:
                for filename, content, mime_type in attachments:
                    try:
                        up = upload_file(drive_svc, MediaIoBaseUpload, folder_id, filename, content, mime_type)
                        if not up:
                            continue
                        file_id, drive_link = up
                        logger.info("[PAGOS_GMAIL] Extrayendo datos con Gemini: %s", filename)
                        data = extract_payment_data(content, filename)
                        if delay_gemini > 0:
                            time.sleep(delay_gemini)
                        row = [
                            subject,
                            data.get("fecha_pago", "No encontrado"),
                            data.get("cedula", "No encontrado"),
                            data.get("monto", "No encontrado"),
                            data.get("numero_referencia", "No encontrado"),
                            drive_link,
                        ]
                        if append_row(sheets_svc, sheet_id, row):
                            item = PagosGmailSyncItem(
                                sync_id=sync_id,
                                correo_origen=sender,
                                asunto=subject,
                                fecha_pago=data.get("fecha_pago"),
                                cedula=data.get("cedula"),
                                monto=data.get("monto"),
                                numero_referencia=data.get("numero_referencia"),
                                drive_file_id=file_id,
                                drive_link=drive_link,
                                sheet_name=sheet_name,
                            )
                            db.add(item)
                            files_ok += 1
                    except Exception as e:
                        logger.warning("Error procesando adjunto %s: %s", filename, e)
            # Marcar como leído para no volver a procesarlo en futuras ejecuciones (solo se listan UNREAD)
            mark_as_read(gmail_svc, msg_id)
            emails_ok += 1
        sync.finished_at = datetime.utcnow()
        sync.status = "success"
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        db.commit()
        return sync_id, "success"
    except Exception as e:
        logger.exception("Pipeline error: %s", e)
        sync.finished_at = datetime.utcnow()
        sync.status = "error"
        sync.error_message = str(e)[:2000]
        sync.emails_processed = emails_ok
        sync.files_processed = files_ok
        db.commit()
        return sync_id, "error"
