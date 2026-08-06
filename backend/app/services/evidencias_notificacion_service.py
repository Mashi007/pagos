"""
Evidencias de notificaciones: escaneo Gmail (itmaster) por etiquetas
DIA SIGUIENTE / 1 CUOTA / 2 O MAS CUOTAS -> PDF unico (correo + anexo) en BD.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
from io import BytesIO
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.evidencia_notificacion import EvidenciaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto

logger = logging.getLogger(__name__)

ETIQUETAS_EVIDENCIAS = (
    "DIA SIGUIENTE",
    "1 CUOTA",
    "2 O MAS CUOTAS",
)

ETIQUETA_CON_ANEXO = "DIA SIGUIENTE"
TIPO_CASO_ANEXO_SISTEMA = "dias_1_retraso"
TIPO_TAB_ANEXO_SISTEMA = "dias_1_retraso"

ITMASTER_EMAIL = "itmaster@rapicreditca.com"
RAPICREDIT_DOMAINS = ("rapicreditca.com", "rapicredit.com")

_RE_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
_RE_FWD_TO = re.compile(
    r"(?:^|\n)\s*(?:To|Para)\s*:\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)


def _norm_email(raw: Optional[str]) -> str:
    if not raw:
        return ""
    _, addr = parseaddr(raw.strip())
    return (addr or raw).strip().lower()


def _es_interno(email: str) -> bool:
    em = _norm_email(email)
    if not em or "@" not in em:
        return True
    if em == ITMASTER_EMAIL:
        return True
    domain = em.rsplit("@", 1)[-1]
    return domain in RAPICREDIT_DOMAINS


def _headers_from_payload(payload: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in payload.get("headers") or []:
        name = (h.get("name") or "").strip()
        if name:
            out[name.lower()] = (h.get("value") or "").strip()
    return out


def _fecha_mensaje(headers: dict[str, str], internal_date_ms: Optional[str]) -> Optional[datetime]:
    date_str = headers.get("date") or ""
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt
        except Exception:
            pass
    if internal_date_ms:
        try:
            return datetime.utcfromtimestamp(int(internal_date_ms) / 1000.0)
        except Exception:
            pass
    return None


def _cedula_por_correo(db: Session, email_raw: str) -> Optional[str]:
    em = _norm_email(email_raw)
    if not em:
        return None
    try:
        rows_main = (
            db.execute(
                select(Cliente.cedula)
                .where(func.lower(func.trim(Cliente.email)) == em)
                .limit(2)
            )
            .scalars()
            .all()
        )
        if len(rows_main) == 1:
            return rows_main[0]
        if len(rows_main) > 1:
            return None
        rows_sec = (
            db.execute(
                select(Cliente.cedula)
                .where(Cliente.email_secundario.isnot(None))
                .where(func.trim(Cliente.email_secundario) != "")
                .where(func.lower(func.trim(Cliente.email_secundario)) == em)
                .limit(2)
            )
            .scalars()
            .all()
        )
        if len(rows_sec) == 1:
            return rows_sec[0]
        return None
    except Exception as ex:
        logger.warning("[EVIDENCIAS] lookup cedula: %s", ex)
        return None


def _email_es_cliente_conocido(db: Session, email_raw: str) -> bool:
    return _cedula_por_correo(db, email_raw) is not None


def _extraer_emails_candidato(texto: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _RE_EMAIL.finditer(texto or ""):
        em = _norm_email(m.group(0))
        if not em or em in seen or _es_interno(em):
            continue
        seen.add(em)
        out.append(em)
    return out


def resolver_email_cliente(
    db: Session,
    *,
    headers: dict[str, str],
    cuerpo: str,
) -> Optional[str]:
    """
    Destinatario real de la notificacion (no itmaster).
    Orden: To/Cc no internos -> X-Original-To -> Para: en reenvio -> emails en cuerpo conocidos en BD.
    """
    for key in ("to", "cc", "delivered-to", "x-original-to", "x-forwarded-to"):
        raw = headers.get(key) or ""
        for part in raw.split(","):
            em = _norm_email(part)
            if em and not _es_interno(em):
                return em

    for m in _RE_FWD_TO.finditer(cuerpo or ""):
        em = _norm_email(m.group(1))
        if em and not _es_interno(em):
            return em

    for em in _extraer_emails_candidato(cuerpo or ""):
        if _email_es_cliente_conocido(db, em):
            return em

    # Ultimo recurso: primer email externo del cuerpo
    candidatos = _extraer_emails_candidato(cuerpo or "")
    return candidatos[0] if candidatos else None


def merge_pdfs(pdf_parts: list[bytes]) -> Optional[bytes]:
    """Fusiona varios PDFs en uno. Si solo hay uno, lo devuelve."""
    parts = [p for p in pdf_parts if p and p[:4] == b"%PDF"]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for blob in parts:
            try:
                reader = PdfReader(BytesIO(blob))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as ex:
                logger.warning("[EVIDENCIAS] omitiendo PDF invalido en merge: %s", ex)
        if len(writer.pages) == 0:
            return parts[0]
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception as ex:
        logger.exception("[EVIDENCIAS] merge_pdfs: %s", ex)
        return parts[0]


def _pdfs_desde_gmail(service: Any, message_id: str, payload: dict) -> list[bytes]:
    from app.services.pagos_gmail.gmail_service import get_attachments_for_message

    out: list[bytes] = []
    try:
        atts = get_attachments_for_message(service, message_id, payload) or []
    except Exception as ex:
        logger.warning("[EVIDENCIAS] adjuntos gmail %s: %s", message_id, ex)
        atts = []
    for filename, content, mime in atts:
        name = (filename or "").lower()
        mime_l = (mime or "").lower()
        if name.endswith(".pdf") or "pdf" in mime_l:
            if content and content[:4] == b"%PDF":
                out.append(content)
    return out


def _pdfs_anexo_sistema(db: Session, email_cliente: str) -> list[bytes]:
    """Preferencia: adjuntos del ultimo envio dias_1_retraso; si no, PDFs fijos del caso."""
    out: list[bytes] = []
    em = _norm_email(email_cliente)
    try:
        envio_id = db.execute(
            select(EnvioNotificacion.id)
            .where(func.lower(func.trim(EnvioNotificacion.email)) == em)
            .where(EnvioNotificacion.tipo_tab == TIPO_TAB_ANEXO_SISTEMA)
            .where(EnvioNotificacion.exito.is_(True))
            .order_by(EnvioNotificacion.fecha_envio.desc())
            .limit(1)
        ).scalar_one_or_none()
        if envio_id:
            rows = (
                db.execute(
                    select(EnvioNotificacionAdjunto.contenido)
                    .where(EnvioNotificacionAdjunto.envio_notificacion_id == envio_id)
                    .order_by(EnvioNotificacionAdjunto.orden)
                )
                .scalars()
                .all()
            )
            for blob in rows:
                if blob and blob[:4] == b"%PDF":
                    out.append(blob)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] anexo desde envios_notificacion: %s", ex)

    if out:
        return out

    try:
        from app.services.adjunto_fijo_cobranza import get_adjuntos_fijos_por_caso

        for _nombre, contenido in get_adjuntos_fijos_por_caso(db, TIPO_CASO_ANEXO_SISTEMA) or []:
            if contenido and contenido[:4] == b"%PDF":
                out.append(contenido)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] anexo fijo sistema: %s", ex)
    return out


def _construir_pdf_evidencia(
    db: Session,
    service: Any,
    *,
    message_id: str,
    payload: dict,
    raw_eml: bytes,
    etiqueta: str,
    email_cliente: str,
) -> tuple[Optional[bytes], bool, str]:
    from app.services.pagos_gmail.email_to_pdf import eml_bytes_to_pdf

    email_pdf = eml_bytes_to_pdf(raw_eml)
    if not email_pdf:
        return None, False, "ninguno"

    partes: list[bytes] = [email_pdf]
    fuente = "ninguno"
    tiene_anexo = False

    if etiqueta == ETIQUETA_CON_ANEXO:
        gmail_pdfs = _pdfs_desde_gmail(service, message_id, payload)
        if gmail_pdfs:
            partes.extend(gmail_pdfs)
            fuente = "gmail"
            tiene_anexo = True
        else:
            sistema_pdfs = _pdfs_anexo_sistema(db, email_cliente)
            if sistema_pdfs:
                partes.extend(sistema_pdfs)
                fuente = "sistema"
                tiene_anexo = True

    merged = merge_pdfs(partes)
    return merged, tiene_anexo, fuente


def buscar_evidencias(
    db: Session,
    *,
    q: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[EvidenciaNotificacion], int]:
    term = (q or "").strip()
    if not term:
        return [], 0

    like = f"%{term.lower()}%"
    # Digitos: tambien buscar cedula sin espacios
    digits = re.sub(r"\D", "", term)
    clauses = [
        EvidenciaNotificacion.email_cliente_norm.ilike(like),
        func.lower(func.coalesce(EvidenciaNotificacion.cedula, "")).ilike(like),
    ]
    if digits and len(digits) >= 5:
        clauses.append(
            func.regexp_replace(func.coalesce(EvidenciaNotificacion.cedula, ""), r"\D", "", "g").ilike(
                f"%{digits}%"
            )
        )

    where = or_(*clauses)
    total = db.execute(
        select(func.count()).select_from(EvidenciaNotificacion).where(where)
    ).scalar() or 0
    rows = (
        db.execute(
            select(EvidenciaNotificacion)
            .where(where)
            .order_by(
                EvidenciaNotificacion.fecha_mensaje.desc().nullslast(),
                EvidenciaNotificacion.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


def obtener_pdf(db: Session, evidencia_id: int) -> Optional[EvidenciaNotificacion]:
    return db.get(EvidenciaNotificacion, evidencia_id)


def procesar_evidencias_gmail(
    db: Session,
    *,
    procesado_por: str,
    max_messages: int = 40,
    presupuesto_segundos: float = 50.0,
) -> dict[str, Any]:
    """
    Escaneo manual: mensajes con etiquetas DIA SIGUIENTE / 1 CUOTA / 2 O MAS CUOTAS.
    Idempotente por gmail_message_id.
    """
    from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
    from app.services.pagos_gmail.gmail_service import (
        build_gmail_service,
        get_existing_user_label_id,
        get_message_all_text_parts,
        get_message_full_payload,
        get_message_raw_bytes,
    )

    creds = get_pagos_gmail_credentials()
    if creds is None:
        return {
            "ok": False,
            "error": "no_credentials",
            "mensaje": "No hay credenciales Gmail (misma conexion que Pagos Gmail / itmaster).",
            "candidatos": 0,
            "revisados": 0,
            "guardados": 0,
            "omitidos": 0,
            "ya_existentes": 0,
            "sin_correo": 0,
            "sin_pdf": 0,
            "etiquetas_faltantes": [],
            "truncado": False,
        }

    service = build_gmail_service(creds)
    etiquetas_faltantes: list[str] = []
    label_queries: list[tuple[str, str]] = []
    for nombre in ETIQUETAS_EVIDENCIAS:
        lid = get_existing_user_label_id(service, nombre)
        if not lid:
            etiquetas_faltantes.append(nombre)
            continue
        label_queries.append((nombre, f'label:"{nombre}"'))

    if not label_queries:
        return {
            "ok": False,
            "error": "labels_missing",
            "mensaje": (
                "No existen en Gmail las etiquetas: "
                + ", ".join(ETIQUETAS_EVIDENCIAS)
                + ". Creelas en itmaster y programe el filtrado."
            ),
            "candidatos": 0,
            "revisados": 0,
            "guardados": 0,
            "omitidos": 0,
            "ya_existentes": 0,
            "sin_correo": 0,
            "sin_pdf": 0,
            "etiquetas_faltantes": etiquetas_faltantes,
            "truncado": False,
        }

    ids_en_bd: set[str] = {
        str(x)
        for x in db.execute(select(EvidenciaNotificacion.gmail_message_id)).scalars().all()
        if x
    }

    lote_objetivo = max(1, min(int(max_messages), 200))
    list_scan_cap = 1000
    # (etiqueta, ref)
    msg_refs: list[tuple[str, dict]] = []
    saltados_ya_bd = 0
    listados_gmail = 0

    for etiqueta, q in label_queries:
        if len(msg_refs) >= lote_objetivo:
            break
        page_token: Optional[str] = None
        while len(msg_refs) < lote_objetivo and listados_gmail < list_scan_cap:
            params: dict[str, Any] = {
                "userId": "me",
                "q": q,
                "maxResults": min(100, list_scan_cap - listados_gmail),
                "includeSpamTrash": False,
            }
            if page_token:
                params["pageToken"] = page_token
            try:
                resp = service.users().messages().list(**params).execute()
            except Exception as e:
                logger.exception("[EVIDENCIAS] list messages %s: %s", etiqueta, e)
                return {
                    "ok": False,
                    "error": "gmail_list_failed",
                    "mensaje": str(e),
                    "candidatos": 0,
                    "revisados": 0,
                    "guardados": 0,
                    "omitidos": 0,
                    "ya_existentes": saltados_ya_bd,
                    "sin_correo": 0,
                    "sin_pdf": 0,
                    "etiquetas_faltantes": etiquetas_faltantes,
                    "truncado": False,
                }
            batch = resp.get("messages") or []
            if not batch:
                break
            for ref in batch:
                listados_gmail += 1
                mid = ref.get("id")
                if not mid:
                    continue
                if mid in ids_en_bd:
                    saltados_ya_bd += 1
                    continue
                # Evitar duplicar el mismo mensaje si tiene varias etiquetas
                if any(r.get("id") == mid for _, r in msg_refs):
                    continue
                msg_refs.append((etiqueta, ref))
                if len(msg_refs) >= lote_objetivo:
                    break
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    candidatos = len(msg_refs)
    revisados = 0
    guardados = 0
    omitidos = 0
    ya_existentes = saltados_ya_bd
    sin_correo = 0
    sin_pdf = 0
    truncado = False
    t0 = time.monotonic()
    deadline = t0 + max(15.0, float(presupuesto_segundos))

    for etiqueta, ref in msg_refs:
        if time.monotonic() >= deadline:
            truncado = True
            break
        mid = ref.get("id")
        if not mid:
            continue
        revisados += 1
        try:
            msg = service.users().messages().get(
                userId="me", id=mid, format="metadata", metadataHeaders=["Subject", "From", "To", "Date", "Cc"]
            ).execute()
        except Exception:
            try:
                msg = {"id": mid, "threadId": ref.get("threadId"), "internalDate": None, "payload": {}}
            except Exception:
                omitidos += 1
                continue

        payload = get_message_full_payload(service, mid) or {}
        headers = _headers_from_payload(payload)
        # Completar headers desde metadata si faltan
        for h in (msg.get("payload") or {}).get("headers") or []:
            name = (h.get("name") or "").strip().lower()
            if name and name not in headers:
                headers[name] = (h.get("value") or "").strip()

        cuerpo = ""
        try:
            cuerpo = get_message_all_text_parts(payload) or ""
        except Exception:
            cuerpo = ""

        email_cliente = resolver_email_cliente(db, headers=headers, cuerpo=cuerpo)
        if not email_cliente:
            sin_correo += 1
            omitidos += 1
            continue

        raw = get_message_raw_bytes(service, mid)
        if not raw:
            sin_pdf += 1
            omitidos += 1
            continue

        pdf_bytes, tiene_anexo, fuente_anexo = _construir_pdf_evidencia(
            db,
            service,
            message_id=mid,
            payload=payload,
            raw_eml=raw,
            etiqueta=etiqueta,
            email_cliente=email_cliente,
        )
        if not pdf_bytes:
            sin_pdf += 1
            omitidos += 1
            continue

        cedula = _cedula_por_correo(db, email_cliente)
        row = EvidenciaNotificacion(
            gmail_message_id=mid,
            gmail_thread_id=msg.get("threadId") or ref.get("threadId"),
            etiqueta_gmail=etiqueta,
            email_cliente=email_cliente,
            email_cliente_norm=_norm_email(email_cliente),
            cedula=cedula,
            asunto=(headers.get("subject") or "")[:500] or None,
            fecha_mensaje=_fecha_mensaje(headers, msg.get("internalDate")),
            pdf_contenido=pdf_bytes,
            pdf_tamano_bytes=len(pdf_bytes),
            tiene_anexo=tiene_anexo,
            fuente_anexo=fuente_anexo,
            procesado_por=(procesado_por or "")[:150] or None,
        )
        try:
            db.add(row)
            db.commit()
            ids_en_bd.add(mid)
            guardados += 1
        except IntegrityError:
            db.rollback()
            ya_existentes += 1
        except Exception as ex:
            db.rollback()
            logger.exception("[EVIDENCIAS] guardar %s: %s", mid, ex)
            omitidos += 1

    mensaje = (
        f"Escanéo: revisados={revisados}, guardados={guardados}, "
        f"ya_en_bd={ya_existentes}, omitidos={omitidos}"
        + (" (truncado por tiempo)" if truncado else "")
    )
    if etiquetas_faltantes:
        mensaje += f". Etiquetas no encontradas en Gmail: {', '.join(etiquetas_faltantes)}"

    return {
        "ok": True,
        "error": None,
        "mensaje": mensaje,
        "candidatos": candidatos,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "sin_correo": sin_correo,
        "sin_pdf": sin_pdf,
        "etiquetas_faltantes": etiquetas_faltantes,
        "truncado": truncado,
    }
