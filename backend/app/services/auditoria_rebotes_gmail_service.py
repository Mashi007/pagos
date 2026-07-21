"""
Escaneo manual de rebotes Gmail etiquetados GMAIL en Inbox de itmaster.

Condicion de busqueda: etiqueta GMAIL (leidos y no leidos).
Clasifica segun texto de Gmail (mal / lleno / temporal / otro),
cruza con clientes (cedula NULL si no hay match) y persiste.
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
from app.models.auditoria_rebote_gmail_kpi import AuditoriaReboteGmailKpi
from app.models.cliente import Cliente
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

NOTIFICACIONES_EMAIL = "notificaciones@rapicreditca.com"
ETIQUETA_GMAIL = "GMAIL"
FRAGMENTO_MAX = 2000

# Condicion de escaneo: etiqueta GMAIL en Inbox (leidos y no leidos).
GMAIL_LIST_QUERY = f"in:inbox label:{ETIQUETA_GMAIL}"

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

_RE_FAILED_RECIPIENTS = re.compile(
    r"(?:X-Failed-Recipients|Failed[- ]Recipients?)\s*:\s*<*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>*",
    re.IGNORECASE,
)

_RE_DSN_EN = re.compile(
    r"(?:recipient\s+failed(?:\s+permanently)?|following\s+recipient|could\s+not\s+be\s+delivered\s+to|"
    r"wasn'?t\s+delivered\s+to|Delivery\s+to\s+the\s+following)\s*:?\s*"
    r"<*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>*",
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
    "dsn",
    "(failure)",
    "(delay)",
    "failure)",
    "delay)",
)


def _norm_email(raw: Optional[str]) -> str:
    if not raw:
        return ""
    _, addr = parseaddr(raw.strip())
    return (addr or raw).strip().lower()


def remitente_es_notificaciones(remitente: str) -> bool:
    em = _norm_email(remitente)
    if em == NOTIFICACIONES_EMAIL.lower():
        return True
    return NOTIFICACIONES_EMAIL.lower() in (remitente or "").lower()


def cuerpo_menciona_notificaciones(texto: str) -> bool:
    return NOTIFICACIONES_EMAIL.lower() in (texto or "").lower()


def parece_rebote_gmail(texto: str, remitente: str = "", asunto: str = "") -> bool:
    blob = f"{remitente}\n{asunto}\n{texto}".lower()
    return any(m in blob for m in _BOUNCE_MARKERS)


def clasificar_observacion(texto: str, asunto: str = "") -> str:
    t = f"{asunto}\n{texto}".lower()
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
            "(failure)",
            "delivery status notification (failure)",
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
            "(delay)",
            "delivery status notification (delay)",
        )
    ):
        return "temporal"
    return "otro"


def extraer_correo_rebotado(texto: str) -> Optional[str]:
    """Extrae el destinatario fallido del cuerpo DSN / aviso Gmail."""
    if not texto:
        return None

    for rx in (
        _RE_FINAL_RECIPIENT,
        _RE_FAILED_RECIPIENTS,
        _RE_ENTREGA_ES,
        _RE_DELIVERED_TO,
        _RE_DSN_EN,
    ):
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


def _cedula_ya_registrada(db: Session, cedula_raw: str) -> bool:
    """True si ya existe una fila con la misma cedula (normalizada) en auditoria_rebotes_gmail."""
    key = texto_cedula_comparable_bd(cedula_raw)
    if not key:
        return False
    encontrado = db.execute(
        select(AuditoriaReboteGmail.id)
        .where(AuditoriaReboteGmail.cedula.isnot(None))
        .where(expr_cedula_normalizada_para_comparar(AuditoriaReboteGmail.cedula) == key)
        .limit(1)
    ).scalar_one_or_none()
    return encontrado is not None


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


def _ensure_kpi_row(db: Session) -> AuditoriaReboteGmailKpi:
    row = db.get(AuditoriaReboteGmailKpi, 1)
    if row is None:
        row = AuditoriaReboteGmailKpi(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def obtener_kpis(db: Session) -> dict[str, Any]:
    """
    KPIs permanentes (acumulados, sobreviven a borrar detalle) + inventario actual.
    """
    kpi = _ensure_kpi_row(db)
    total_actual = db.execute(select(func.count()).select_from(AuditoriaReboteGmail)).scalar() or 0
    obs_rows = db.execute(
        select(AuditoriaReboteGmail.observaciones, func.count())
        .group_by(AuditoriaReboteGmail.observaciones)
    ).all()
    actual_por_obs = {"mal": 0, "lleno": 0, "temporal": 0, "otro": 0}
    for obs, cnt in obs_rows:
        key = (obs or "otro").strip().lower()
        if key not in actual_por_obs:
            key = "otro"
        actual_por_obs[key] = int(cnt or 0)

    return {
        "total_escaneados": int(kpi.total_escaneados or 0),
        "total_guardados": int(kpi.total_guardados or 0),
        "total_omitidos": int(kpi.total_omitidos or 0),
        "total_sin_correo": int(kpi.total_sin_correo or 0),
        "total_sin_cedula": int(kpi.total_sin_cedula or 0),
        "total_cedula_duplicada": int(kpi.total_cedula_duplicada or 0),
        "total_ya_existentes": int(kpi.total_ya_existentes or 0),
        "total_mal": int(kpi.total_mal or 0),
        "total_lleno": int(kpi.total_lleno or 0),
        "total_temporal": int(kpi.total_temporal or 0),
        "total_otro": int(kpi.total_otro or 0),
        "total_corridas": int(kpi.total_corridas or 0),
        "ultima_corrida_at": kpi.ultima_corrida_at.isoformat() if kpi.ultima_corrida_at else None,
        "registros_actuales": int(total_actual),
        "actual_mal": actual_por_obs["mal"],
        "actual_lleno": actual_por_obs["lleno"],
        "actual_temporal": actual_por_obs["temporal"],
        "actual_otro": actual_por_obs["otro"],
    }


def _aplicar_kpis_corrida(
    db: Session,
    *,
    revisados: int,
    guardados: int,
    omitidos: int,
    sin_correo: int,
    sin_cedula: int,
    cedula_duplicada: int,
    ya_existentes: int,
    guardados_por_obs: dict[str, int],
) -> None:
    kpi = _ensure_kpi_row(db)
    kpi.total_escaneados = int(kpi.total_escaneados or 0) + int(revisados or 0)
    kpi.total_guardados = int(kpi.total_guardados or 0) + int(guardados or 0)
    kpi.total_omitidos = int(kpi.total_omitidos or 0) + int(omitidos or 0)
    kpi.total_sin_correo = int(kpi.total_sin_correo or 0) + int(sin_correo or 0)
    kpi.total_sin_cedula = int(kpi.total_sin_cedula or 0) + int(sin_cedula or 0)
    kpi.total_cedula_duplicada = int(kpi.total_cedula_duplicada or 0) + int(
        cedula_duplicada or 0
    )
    kpi.total_ya_existentes = int(kpi.total_ya_existentes or 0) + int(ya_existentes or 0)
    kpi.total_mal = int(kpi.total_mal or 0) + int(guardados_por_obs.get("mal", 0))
    kpi.total_lleno = int(kpi.total_lleno or 0) + int(guardados_por_obs.get("lleno", 0))
    kpi.total_temporal = int(kpi.total_temporal or 0) + int(
        guardados_por_obs.get("temporal", 0)
    )
    kpi.total_otro = int(kpi.total_otro or 0) + int(guardados_por_obs.get("otro", 0))
    kpi.total_corridas = int(kpi.total_corridas or 0) + 1
    kpi.ultima_corrida_at = datetime.utcnow()
    kpi.actualizado_en = datetime.utcnow()
    db.add(kpi)
    db.commit()


def procesar_rebotes_gmail(
    db: Session,
    *,
    procesado_por: str,
    max_messages: int = 40,
    presupuesto_segundos: float = 50.0,
) -> dict[str, Any]:
    """
    Escanea Inbox con etiqueta GMAIL, guarda filas nuevas.
    Limita lote y tiempo para no morir por timeout/SIGTERM en Render.
    """
    import time

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
            "candidatos": 0,
            "revisados": 0,
            "guardados": 0,
            "omitidos": 0,
            "ya_existentes": 0,
            "etiquetados": 0,
            "sin_correo": 0,
            "sin_cedula": 0,
            "cedula_duplicada": 0,
            "truncado": False,
        }

    service = build_gmail_service(creds)
    label_id = ensure_user_label_id(service, ETIQUETA_GMAIL)

    # IDs ya guardados: hay que paginar Gmail mas alla de los primeros N
    # (Gmail siempre devuelve primero los mas recientes; si esos ya estan en BD
    # el lote quedaba en "40 ya en BD" y nunca avanzaba).
    ids_en_bd: set[str] = {
        str(x)
        for x in db.execute(select(AuditoriaReboteGmail.gmail_message_id)).scalars().all()
        if x
    }

    lote_objetivo = max(1, min(int(max_messages), 200))
    list_scan_cap = 1000  # max mensajes Gmail a recorrer buscando pendientes
    msg_refs: list[dict] = []
    page_token: Optional[str] = None
    listados_gmail = 0
    saltados_ya_bd = 0

    while len(msg_refs) < lote_objetivo and listados_gmail < list_scan_cap:
        params: dict[str, Any] = {
            "userId": "me",
            "q": GMAIL_LIST_QUERY,
            "maxResults": min(100, list_scan_cap - listados_gmail),
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
                "candidatos": 0,
                "revisados": 0,
                "guardados": 0,
                "omitidos": 0,
                "ya_existentes": 0,
                "etiquetados": 0,
                "sin_correo": 0,
                "sin_cedula": 0,
                "cedula_duplicada": 0,
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
            msg_refs.append(ref)
            if len(msg_refs) >= lote_objetivo:
                break
            if listados_gmail >= list_scan_cap:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    candidatos = len(msg_refs)
    logger.info(
        "[AUDITORIA_REBOTES_GMAIL] q=%r pendientes=%s listados_gmail=%s "
        "saltados_ya_bd=%s lote=%s presupuesto_s=%s",
        GMAIL_LIST_QUERY,
        candidatos,
        listados_gmail,
        saltados_ya_bd,
        lote_objetivo,
        presupuesto_segundos,
    )

    revisados = 0
    guardados = 0
    omitidos = 0
    ya_existentes = saltados_ya_bd  # ya contabilizados en el listado
    etiquetados = 0
    sin_correo = 0
    sin_cedula = 0
    cedula_duplicada = 0
    truncado = False
    guardados_por_obs: dict[str, int] = {"mal": 0, "lleno": 0, "temporal": 0, "otro": 0}
    t0 = time.monotonic()
    deadline = t0 + max(15.0, float(presupuesto_segundos))

    if candidatos == 0:
        mensaje = (
            f"No hay pendientes nuevos con q={GMAIL_LIST_QUERY!r} "
            f"(recorridos {listados_gmail} en Gmail, {saltados_ya_bd} ya en BD)."
        )
        try:
            _aplicar_kpis_corrida(
                db,
                revisados=0,
                guardados=0,
                omitidos=0,
                sin_correo=0,
                sin_cedula=0,
                cedula_duplicada=0,
                ya_existentes=saltados_ya_bd,
                guardados_por_obs=guardados_por_obs,
            )
        except Exception as e:
            logger.warning("[AUDITORIA_REBOTES_GMAIL] actualizar kpis: %s", e)
        return {
            "ok": True,
            "error": None,
            "mensaje": mensaje,
            "query": GMAIL_LIST_QUERY,
            "etiqueta": ETIQUETA_GMAIL,
            "candidatos": 0,
            "revisados": 0,
            "guardados": 0,
            "omitidos": 0,
            "ya_existentes": saltados_ya_bd,
            "etiquetados": 0,
            "sin_correo": 0,
            "sin_cedula": 0,
            "cedula_duplicada": 0,
            "truncado": False,
            "listados_gmail": listados_gmail,
        }

    for ref in msg_refs:
        if time.monotonic() >= deadline:
            truncado = True
            logger.warning(
                "[AUDITORIA_REBOTES_GMAIL] presupuesto agotado tras %.1fs "
                "(revisados=%s guardados=%s candidatos=%s). Pulse Procesar de nuevo.",
                time.monotonic() - t0,
                revisados,
                guardados,
                candidatos,
            )
            break

        mid = ref.get("id")
        if not mid:
            continue

        if mid in ids_en_bd:
            ya_existentes += 1
            revisados += 1
            continue

        revisados += 1
        if revisados % 10 == 0:
            logger.info(
                "[AUDITORIA_REBOTES_GMAIL] progreso revisados=%s/%s guardados=%s elapsed=%.1fs",
                revisados,
                candidatos,
                guardados,
                time.monotonic() - t0,
            )

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

        if not parece_rebote_gmail(texto, remitente, asunto):
            omitidos += 1
            continue

        correo = extraer_correo_rebotado(texto)
        if not correo:
            sin_correo += 1
            omitidos += 1
            continue

        obs = clasificar_observacion(texto, asunto)
        cedula_raw = _cedula_por_correo(db, correo)
        cedula = normalizar_cedula_almacenamiento(cedula_raw) if cedula_raw else None
        if not cedula:
            sin_cedula += 1
            omitidos += 1
            continue

        fecha_msg = _fecha_mensaje(headers, full.get("internalDate"))

        if _cedula_ya_registrada(db, cedula):
            cedula_duplicada += 1
            ya_existentes += 1
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
            ids_en_bd.add(mid)
            obs_key = (obs or "otro").strip().lower()
            if obs_key not in guardados_por_obs:
                obs_key = "otro"
            guardados_por_obs[obs_key] = guardados_por_obs.get(obs_key, 0) + 1
        except IntegrityError:
            db.rollback()
            ya_existentes += 1
            ids_en_bd.add(mid)
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

    try:
        _aplicar_kpis_corrida(
            db,
            revisados=revisados,
            guardados=guardados,
            omitidos=omitidos,
            sin_correo=sin_correo,
            sin_cedula=sin_cedula,
            cedula_duplicada=cedula_duplicada,
            ya_existentes=ya_existentes,
            guardados_por_obs=guardados_por_obs,
        )
    except Exception as e:
        logger.warning("[AUDITORIA_REBOTES_GMAIL] actualizar kpis: %s", e)

    mensaje = None
    if truncado:
        mensaje = (
            f"Lote parcial por limite de tiempo (~{int(presupuesto_segundos)}s): "
            f"revisados {revisados}/{candidatos}, guardados {guardados}. "
            "Pulse Procesar ahora de nuevo para continuar."
        )

    logger.info(
        "[AUDITORIA_REBOTES_GMAIL] fin pendientes=%s revisados=%s guardados=%s "
        "omitidos=%s ya_existentes=%s listados_gmail=%s truncado=%s elapsed=%.1fs",
        candidatos,
        revisados,
        guardados,
        omitidos,
        ya_existentes,
        listados_gmail,
        truncado,
        time.monotonic() - t0,
    )

    return {
        "ok": True,
        "error": None,
        "mensaje": mensaje,
        "query": GMAIL_LIST_QUERY,
        "etiqueta": ETIQUETA_GMAIL,
        "candidatos": candidatos,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "etiquetados": etiquetados,
        "sin_correo": sin_correo,
        "sin_cedula": sin_cedula,
        "cedula_duplicada": cedula_duplicada,
        "truncado": truncado,
        "listados_gmail": listados_gmail,
    }
