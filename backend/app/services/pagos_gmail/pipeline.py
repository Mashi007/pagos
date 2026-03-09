"""
Orquestación: Gmail -> Drive (imágenes) -> Gemini (extracción) -> BD (PostgreSQL).
Google Sheets eliminado: el Excel se genera directamente desde la BD.
Flujo por correo:
  1. Listar no leídos en Gmail
  2. Por cada correo: obtener payload completo, extraer imágenes/PDFs
  3. Subir cada imagen a Drive (carpeta por fecha)
  4. Enviar imagen a Gemini → extraer fecha_pago, cedula, monto, numero_referencia
  5. Guardar fila en BD (PagosGmailSyncItem) — commit incremental por correo
  6. Marcar correo como leído
El Excel se descarga vía GET /pagos/gmail/download-excel (generado desde BD).
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
    get_message_date,
    get_message_full_payload,
    list_unread_with_attachments,
    mark_as_read,
)
from app.services.pagos_gmail.gemini_service import extract_payment_data, PAGOS_NA
from app.services.pagos_gmail.helpers import (
    extract_sender_email,
    formatear_cedula,
    get_folder_name_from_date,
    get_sheet_name_for_date,
)

logger = logging.getLogger(__name__)


def run_pipeline(db: Session, existing_sync_id: Optional[int] = None) -> tuple[Optional[int], str]:
    """
    Ejecuta el pipeline Gmail -> Drive -> Gemini -> BD.
    Returns (sync_id, "success"|"error"|"no_credentials").
    """
    logger.warning("[PAGOS_GMAIL] ▶ INICIO pipeline (existing_sync_id=%s)", existing_sync_id)
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
        logger.warning("[PAGOS_GMAIL] → Listando correos no leídos en Gmail...")
        messages = list_unread_with_attachments(gmail_svc)
        max_emails = getattr(settings, "PAGOS_GMAIL_MAX_EMAILS_PER_RUN", 0)
        total_unread = len(messages)
        logger.warning("[PAGOS_GMAIL] ✓ Correos no leídos: %d (máx por ejecución: %s)", total_unread, max_emails or "sin límite")
        if total_unread == 0:
            logger.warning("[PAGOS_GMAIL] ℹ No hay correos no leídos — pipeline termina")
        if max_emails and max_emails > 0 and total_unread > max_emails:
            messages = messages[:max_emails]
            logger.warning("[PAGOS_GMAIL] ℹ Limitado a %d correos (de %d no leídos)", max_emails, total_unread)

        delay_gemini = getattr(settings, "PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS", 0) or 0

        for msg_info in messages:
            msg_id = msg_info["id"]
            payload = msg_info["payload"]
            headers = msg_info["headers"]
            from_h = headers.get("from") or headers.get("From") or ""
            sender = extract_sender_email(from_h)
            subject = (headers.get("subject") or headers.get("Subject") or "").strip() or sender
            msg_date = get_message_date(headers)
            # sheet_name se conserva en BD para agrupar/filtrar por fecha aunque no usemos Sheets
            sheet_name = get_sheet_name_for_date(msg_date)
            folder_name = get_folder_name_from_date(msg_date)

            logger.warning("[PAGOS_GMAIL] ── Correo %d/%d id=%s | de=%s | asunto=%s",
                emails_ok + 1, len(messages), msg_id, sender[:40], subject[:50])

            # Crear carpeta Drive para las imágenes de este correo
            folder_id = get_or_create_folder(drive_svc, folder_name)
            if not folder_id:
                drive_errors += 1
                logger.warning("[PAGOS_GMAIL] ✗ No se pudo crear carpeta Drive '%s' — omitiendo msg %s", folder_name, msg_id)
                continue

            logger.warning("[PAGOS_GMAIL]   folder_id=%s", folder_id)

            # Obtener payload completo del correo
            full_payload = get_message_full_payload(gmail_svc, msg_id)
            if not full_payload and payload.get("parts"):
                full_payload = payload

            # Extraer remitente original del Fwd: para trazabilidad
            forwarded_raw = extract_forwarded_sender(full_payload) if full_payload else None
            if forwarded_raw:
                forwarded_email = extract_sender_email(forwarded_raw) or forwarded_raw
                sender = forwarded_email
                if "@" not in subject:
                    subject = forwarded_raw
                logger.warning("[PAGOS_GMAIL]   Fwd detectado → correo_origen=%s", sender[:60])

            # Extraer imágenes/PDFs del correo
            attachments = get_all_images_and_files_for_message(gmail_svc, msg_id, full_payload)
            logger.warning("[PAGOS_GMAIL]   imágenes encontradas: %d — %s",
                len(attachments),
                ", ".join(f"{f}({len(c)}B)" for f, c, _ in attachments) if attachments else "ninguno")

            mensaje_tiene_fila_valida = False
            fila_guardada = False

            def _guardar_en_bd(correo: str, fecha: str, cedula: str, monto: str,
                               referencia: str, drive_file_id=None, drive_lnk="") -> bool:
                """Persiste fila directamente en BD (sin Sheets). Retorna True si tuvo éxito."""
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
                # Sin imágenes: guardar fila NA para trazabilidad
                _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA)
                logger.warning("[PAGOS_GMAIL]   Sin imágenes → fila NA guardada")
            else:
                for filename, content, mime_type in attachments:
                    try:
                        # Subir imagen a Drive
                        up = upload_file(drive_svc, MediaIoBaseUpload, folder_id, filename, content, mime_type)
                        file_id = None
                        drive_link = ""
                        if up:
                            file_id, drive_link = up
                            logger.warning("[PAGOS_GMAIL]   Drive OK: %s → %s", filename, drive_link[:60])

                        # Extraer datos con Gemini
                        data = extract_payment_data(content, filename)
                        if delay_gemini > 0:
                            time.sleep(delay_gemini)

                        f = _v(data.get("fecha_pago"))
                        c = formatear_cedula(_v(data.get("cedula")))
                        m = _v(data.get("monto"))
                        r = _v(data.get("numero_referencia"))
                        tiene_valido = bool(f or (c and c != PAGOS_NA) or m or r)
                        if tiene_valido:
                            mensaje_tiene_fila_valida = True

                        _guardar_en_bd(
                            sender,
                            f or PAGOS_NA, c or PAGOS_NA, m or PAGOS_NA, r or PAGOS_NA,
                            drive_file_id=file_id, drive_lnk=drive_link or "",
                        )
                    except Exception as e:
                        logger.warning("[PAGOS_GMAIL]   Error procesando %s: %s", filename, e)
                        _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA)

            # Garantía: al menos 1 fila por correo
            if not fila_guardada:
                logger.warning("[PAGOS_GMAIL]   ✗ Sin fila guardada para %s — fila NA de respaldo", msg_id)
                _guardar_en_bd(sender, PAGOS_NA, PAGOS_NA, PAGOS_NA, PAGOS_NA)

            # Marcar correo como leído
            mark_as_read(gmail_svc, msg_id)
            if not mensaje_tiene_fila_valida:
                logger.warning("[PAGOS_GMAIL]   Correo marcado leído (todo NA)")
            emails_ok += 1

            # Commit incremental: persiste cada correo de inmediato
            sync.emails_processed = emails_ok
            sync.files_processed = files_ok
            db.commit()

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
