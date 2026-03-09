"""
Orquestación: Gmail -> Drive -> Gemini -> Sheets; marcar correo leído; registrar en BD (pagos_gmail_sync, pagos_gmail_sync_item).
Solo se procesan correos NO LEÍDOS que tengan adjunto o imagen válida (imagen/PDF).
Una vez procesado con datos válidos se marca como leído; si todo sale NA se deja no leído para reintento.
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
from app.services.pagos_gmail.gemini_service import extract_payment_data, PAGOS_NA
from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    get_folder_name_from_date,
    get_sheet_name_for_date,
)
from app.services.pagos_gmail.sheets_service import append_row

logger = logging.getLogger(__name__)

# NA = No aplica: no hubo la información o al ser manual no se identifica (mismas columnas en adjuntos y cuerpo)


def run_pipeline(db: Session, existing_sync_id: Optional[int] = None) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline completo. Si se pasa existing_sync_id usa ese registro (pre-creado por el endpoint
    para evitar timeout en la respuesta HTTP); si no, crea uno nuevo.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
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
        return existing_sync_id, "no_credentials"
    drive_svc, MediaIoBaseUpload = build_drive_service(creds)
    gmail_svc = build_gmail_service(creds)
    from googleapiclient.discovery import build
    sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
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
            mensaje_tiene_fila_valida = False
            if len(attachments) == 0:
                # Sin adjuntos ni imágenes en cuerpo: fila NA
                row = [subject, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, ""]
                if append_row(sheets_svc, sheet_id, row):
                    item = PagosGmailSyncItem(
                        sync_id=sync_id,
                        correo_origen=sender,
                        asunto=subject,
                        fecha_pago=PAGOS_NA,
                        cedula=PAGOS_NA,
                        monto=PAGOS_NA,
                        numero_referencia=PAGOS_NA,
                        drive_file_id=None,
                        drive_link=None,
                        sheet_name=sheet_name,
                    )
                    db.add(item)
                    files_ok += 1
                logger.info("[PAGOS_GMAIL] Correo sin adjuntos ni imágenes: fila NA")
            else:
                # 1 o más imágenes/PDFs: procesar cada uno con Gemini (incluye imágenes dentro de Fwd:)
                for filename, content, mime_type in attachments:
                    try:
                        up = upload_file(drive_svc, MediaIoBaseUpload, folder_id, filename, content, mime_type)
                        file_id = None
                        drive_link = ""
                        if up:
                            file_id, drive_link = up
                        logger.info("[PAGOS_GMAIL] Extrayendo datos con Gemini: %s", filename)
                        data = extract_payment_data(content, filename)
                        if delay_gemini > 0:
                            time.sleep(delay_gemini)
                        # ¿Información válida? Al menos un campo distinto de vacío o NA
                        def _v(x: Optional[str]) -> str:
                            v = (x or "").strip()
                            return v if v and v.upper() != "NA" else ""
                        f = _v(data.get("fecha_pago"))
                        c = _v(data.get("cedula"))
                        m = _v(data.get("monto"))
                        r = _v(data.get("numero_referencia"))
                        tiene_valido = bool(f or c or m or r)
                        if tiene_valido:
                            mensaje_tiene_fila_valida = True
                            row = [subject, f or PAGOS_NA, c or PAGOS_NA, m or PAGOS_NA, r or PAGOS_NA, drive_link or ""]
                            item_vals = {"fecha_pago": f or PAGOS_NA, "cedula": c or PAGOS_NA, "monto": m or PAGOS_NA, "numero_referencia": r or PAGOS_NA}
                        else:
                            row = [subject, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, drive_link or ""]
                            item_vals = {"fecha_pago": PAGOS_NA, "cedula": PAGOS_NA, "monto": PAGOS_NA, "numero_referencia": PAGOS_NA}
                        if append_row(sheets_svc, sheet_id, row):
                            item = PagosGmailSyncItem(
                                sync_id=sync_id,
                                correo_origen=sender,
                                asunto=subject,
                                fecha_pago=item_vals["fecha_pago"],
                                cedula=item_vals["cedula"],
                                monto=item_vals["monto"],
                                numero_referencia=item_vals["numero_referencia"],
                                drive_file_id=file_id,
                                drive_link=drive_link or None,
                                sheet_name=sheet_name,
                            )
                            db.add(item)
                            files_ok += 1
                    except Exception as e:
                        logger.warning("Error procesando adjunto/cuerpo %s: %s", filename, e)
                        row = [subject, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA, ""]
                        if append_row(sheets_svc, sheet_id, row):
                            item = PagosGmailSyncItem(
                                sync_id=sync_id,
                                correo_origen=sender,
                                asunto=subject,
                                fecha_pago=PAGOS_NA,
                                cedula=PAGOS_NA,
                                monto=PAGOS_NA,
                                numero_referencia=PAGOS_NA,
                                drive_file_id=None,
                                drive_link=None,
                                sheet_name=sheet_name,
                            )
                            db.add(item)
                            files_ok += 1
            # Marcar siempre como leído una vez procesado (evita que el mismo correo se reprocese
            # indefinidamente si Gemini no puede extraer datos — ej. notificaciones de vencimiento).
            mark_as_read(gmail_svc, msg_id)
            if not mensaje_tiene_fila_valida:
                logger.info("[PAGOS_GMAIL] Correo procesado con todo NA: marcado como leído (no era comprobante de pago o imagen ilegible)")
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
