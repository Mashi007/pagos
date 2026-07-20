"""
Escaneo manual de rebotes Gmail en bandeja Principal de itmaster.

Clave: el cuerpo debe mencionar notificaciones@rapicreditca.com.
Clasifica segun texto de Gmail (mal / lleno / temporal / otro),
cruza con clientes (cedula NULL si no hay match), etiqueta GMAIL y persiste.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria_rebote_gmail import AuditoriaReboteGmail
from app.models.cliente import Cliente

logger = logging.getLogger(__name__)

NOTIFICACIONES_EMAIL = "notificaciones@rapicreditca.com"
ETIQUETA_GMAIL = "GMAIL"
FRAGMENTO_MAX = 2000

# Bandeja Principal + menciones a notificaciones; excluye ya etiquetados GMAIL.
GMAIL_LIST_QUERY = (
    f'in:inbox category:primary ("{NOTIFICACIONES_EMAIL}") -label:{ETIQUETA_GMAIL}'
)

_RE_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

_RE_FINAL_RECIPIENT = re.compile(
    r"(?:Final-Recipient|Original-Recipient)\s*:\s*rfc822\s*;\s*([^\s<>]+)",
    re.IGNORECASE,
)

_RE_ENTREGA_ES = re.compile(
    r"(?:entregar(?:\s+el)?\s+mensaje\s+a|no\s+se\s+ha\s+entregado\s+a|"
    r"tu\s+mensaje\s+no\s+se\s+ha\s+entregado\s+a)\s+"
    r"<*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>*",
    re.IGNORECASE,
)

_RE_DELIVERED_TO = re.compile(
    r"(?:delivered\s+to|Address:\s*)<*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>*",
    re.IGNORECASE,
)

_BOUNCE_MARKERS = (
    "mailer-daemon",
    "mail delivery subsystem",
    "delivery status notification",
    "undeliverable",
    "no se ha completado la entrega",
    "no se ha encontrado la dirección",
    "no se ha encontrado la direccion",
    "address not found",
    "mailbox full",
    "problema temporal",
    "temporary problem",
    "could not be delivered",
    "wasn't delivered",
    "was not delivered",
)


def _norm_email(raw: Optional[str]) -> str:
    if not raw:
        return ""
    _, addr = parseaddr(raw.strip())
    return (addr or raw).strip().lower()


def cuerpo_menciona_notificaciones(texto: str) -> bool:
    return NOTIFICACIONES_EMAIL.lower() in (texto or "").lower()


def parece_rebote_gmail(texto: str, remitente: str = "") -> bool:
    blob = f"{remitente}\n{texto}".lower()
    return any(m in blob for m in _BOUNCE_MARKERS)


def clasificar_observacion(texto: str) -> str:
    t = (texto or "").lower()
    if any(
        x in t
        for x in (
            "no se ha encontrado la dirección",
            "no se ha encontrado la direccion",
            "address not found",
            "user unknown",
            "does not exist",
            "no such user",
            "recipient address rejected",
            "mailbox unavailable",
            "invalid recipient",
        )
    ):
        return "mal"
    if any(
        x in t
        for x in (
            "buzón lleno",
            "buzon lleno",
            "mailbox full",
            "over quota",
            "quota exceeded",
            "inbox is full",
            "insufficient system storage",
        )
    ):
        return "lleno"
    if any(
        x in t
        for x in (
            "problema temporal",
            "temporary problem",
            "temporary failure",
            "try again later",
            "deferred",
            "will keep trying",
            "seguirá intentando",
            "seguira intentando",
            "delay",
        )
    ):
        return "temporal"
    return "otro"


def extraer_correo_rebotado(texto: str) -> Optional[str]:
    """Extrae el destinatario fallido del cuerpo DSN / aviso Gmail."""
    if not texto:
        return None

    for rx in (_RE_FINAL_RECIPIENT, _RE_ENTREGA_ES, _RE_DELIVERED_TO):
        m = rx.search(texto)
        if m:
            em = _norm_email(m.group(1))
            if em and em != NOTIFICACIONES_EMAIL.lower() and "mailer-daemon" not in em:
                return em

    # Fallback: primer email del cuerpo que no sea notificaciones / mailer-daemon / google
    skip_domains = ("googlemail.com", "google.com", "mail.gmail.com")
    for m in _RE_EMAIL.finditer(texto):
        em = _norm_email(m.group(0))
        if not em or em == NOTIFICACIONES_EMAIL.lower():
            continue
        if "mailer-daemon" in em:
            continue
        if any(em.endswith("@" + d) or em.endswith("." + d) for d in skip_domains):
            continue
        return em
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
        logger.warning("[AUDITORIA_REBOTES_GMAIL] lookup cedula: %s", ex)
        return None


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


def listar_rebotes(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AuditoriaReboteGmail], int]:
    total = db.execute(select(func.count()).select_from(AuditoriaReboteGmail)).scalar() or 0
    rows = (
        db.execute(
            select(AuditoriaReboteGmail)
            .order_by(AuditoriaReboteGmail.fecha_registro.desc(), AuditoriaReboteGmail.id.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


def borrar_todos(db: Session) -> int:
    result = db.execute(delete(AuditoriaReboteGmail))
    db.commit()
    return int(result.rowcount or 0)


def procesar_rebotes_gmail(
    db: Session,
    *,
    procesado_por: str,
    max_messages: int = 200,
) -> dict[str, Any]:
    """
    Escanea Primary de la cuenta Gmail conectada (itmaster), guarda filas nuevas y etiqueta GMAIL.
    """
    from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
    from app.services.pagos_gmail.gmail_service import (
        add_message_user_labels_only,
        build_gmail_service,
        ensure_user_label_id,
        get_message_all_text_parts,
        get_message_body_text,
    )

    creds = get_pagos_gmail_credentials()
    if creds is None:
        return {
            "ok": False,
            "error": "no_credentials",
            "mensaje": "No hay credenciales Gmail configuradas (misma conexion que Actualizaciones > Gmail).",
            "revisados": 0,
            "guardados": 0,
            "omitidos": 0,
            "ya_existentes": 0,
            "etiquetados": 0,
            "sin_correo": 0,
        }

    service = build_gmail_service(creds)
    label_id = ensure_user_label_id(service, ETIQUETA_GMAIL)

    msg_refs: list[dict] = []
    page_token: Optional[str] = None
    hard_cap = max(1, min(int(max_messages), 1000))

    while len(msg_refs) < hard_cap:
        params: dict[str, Any] = {
            "userId": "me",
            "q": GMAIL_LIST_QUERY,
            "maxResults": min(100, hard_cap - len(msg_refs)),
            "includeSpamTrash": False,
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            resp = service.users().messages().list(**params).execute()
        except Exception as e:
            logger.exception("[AUDITORIA_REBOTES_GMAIL] list messages: %s", e)
            return {
                "ok": False,
                "error": "gmail_list_failed",
                "mensaje": str(e),
                "revisados": 0,
                "guardados": 0,
                "omitidos": 0,
                "ya_existentes": 0,
                "etiquetados": 0,
                "sin_correo": 0,
            }
        batch = resp.get("messages") or []
        msg_refs.extend(batch)
        page_token = resp.get("nextPageToken")
        if not page_token or not batch:
            break

    msg_refs = msg_refs[:hard_cap]
    logger.info(
        "[AUDITORIA_REBOTES_GMAIL] q=%r candidatos=%s",
        GMAIL_LIST_QUERY,
        len(msg_refs),
    )

    revisados = 0
    guardados = 0
    omitidos = 0
    ya_existentes = 0
    etiquetados = 0
    sin_correo = 0

    for ref in msg_refs:
        mid = ref.get("id")
        if not mid:
            continue
        revisados += 1
        try:
            full = (
                service.users()
                .messages()
                .get(userId="me", id=mid, format="full")
                .execute()
            )
        except Exception as e:
            logger.warning("[AUDITORIA_REBOTES_GMAIL] get %s: %s", mid, e)
            omitidos += 1
            continue

        payload = full.get("payload") or {}
        headers = _headers_from_payload(payload)
        body = get_message_body_text(payload) or ""
        all_text = get_message_all_text_parts(payload) or ""
        snippet = (full.get("snippet") or "").strip()
        texto = all_text or body or snippet
        remitente = headers.get("from") or ""
        asunto = headers.get("subject") or ""

        if not cuerpo_menciona_notificaciones(texto):
            omitidos += 1
            continue

        if not parece_rebote_gmail(texto, remitente):
            omitidos += 1
            continue

        correo = extraer_correo_rebotado(texto)
        if not correo:
            sin_correo += 1
            omitidos += 1
            continue

        obs = clasificar_observacion(texto)
        cedula = _cedula_por_correo(db, correo)
        fecha_msg = _fecha_mensaje(headers, full.get("internalDate"))

        existente = db.execute(
            select(AuditoriaReboteGmail.id).where(
                AuditoriaReboteGmail.gmail_message_id == mid
            )
        ).scalar_one_or_none()
        if existente:
            ya_existentes += 1
            if label_id:
                try:
                    add_message_user_labels_only(service, mid, [label_id])
                    etiquetados += 1
                except Exception:
                    pass
            continue

        row = AuditoriaReboteGmail(
            gmail_message_id=mid,
            gmail_thread_id=full.get("threadId") or ref.get("threadId"),
            cedula=cedula,
            correo=correo,
            observaciones=obs,
            asunto_gmail=(asunto or "")[:500] or None,
            remitente_detectado=(remitente or "")[:255] or None,
            etiqueta_gmail=ETIQUETA_GMAIL,
            fecha_mensaje=fecha_msg,
            procesado_por=(procesado_por or "")[:150] or None,
            fragmento_cuerpo=(texto or "")[:FRAGMENTO_MAX] or None,
        )
        db.add(row)
        try:
            db.commit()
            guardados += 1
        except IntegrityError:
            db.rollback()
            ya_existentes += 1
        except Exception as e:
            db.rollback()
            logger.warning("[AUDITORIA_REBOTES_GMAIL] insert %s: %s", mid, e)
            omitidos += 1
            continue

        if label_id:
            try:
                add_message_user_labels_only(service, mid, [label_id])
                etiquetados += 1
            except Exception as e:
                logger.warning("[AUDITORIA_REBOTES_GMAIL] label %s: %s", mid, e)

    return {
        "ok": True,
        "error": None,
        "mensaje": None,
        "query": GMAIL_LIST_QUERY,
        "etiqueta": ETIQUETA_GMAIL,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "etiquetados": etiquetados,
        "sin_correo": sin_correo,
    }
