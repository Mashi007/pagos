"""
Servicio de escaneo Auditoría Email (buzón cobranza@).

Flujo (manifest 2.4+): filtro Gmail (con o sin etiqueta; opcional ``-label:ANALIZADOS``) → lotes ≤100 → pipeline
Pagos Gmail con ``defer_autoconciliacion=True`` (solo OCR/digitaliza) → materializar
cola Recibos (pending) → etiqueta ANALIZADOS **adicional** (no quita MERCANTIL/BNC/…):
si hay recibo, si ya tenía etiqueta de usuario, o si digitalizó.
La alta a cartera / cuotas ocurre solo al Aprobar en Recibos; E/F o fallo de
validadores → ``pagos_con_errores``.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from email.utils import parseaddr
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auditoria_email import (
    AuditoriaEmailMessage,
    AuditoriaEmailReceipt,
    AuditoriaEmailScan,
)
from app.services.auditoria_email.pipelines import PIPELINE_CATALOG
from app.services.auditoria_email.query import (
    analizados_label_name,
    apply_preset,
    build_gmail_query,
    criteria_needs_payload_inspection,
    has_date_bound,
    matches_criteria,
)
from app.services.pagos_gmail.credentials import (
    cobranza_oauth_config_status,
    cobranza_tokens_ready,
    load_cobranza_gmail_token_payload,
)

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "2.4.0"
LOT_SIZE_MAX = 100
# Escaneo stuck en running (HTTP cortado / worker caído) → se puede reanudar.
# ≥45 min: un PDF/OCR pesado puede superar 15 min sin latido entre mensajes.
SCAN_STALE_RUNNING_MINUTES = 45
# running en BD pero sin hilo local (deploy/crash): pausar tras este idle.
# ≥10 min: list+fetch de un lote Gmail (50 msgs) puede tardar varios minutos
# sin aún crear filas en_cola; un umbral de 3 min + heal en GET mataba el job
# en «Preparando lote…» con Listados=0.
SCAN_ORPHAN_RUNNING_MINUTES = 10
# Lock de Pagos Gmail tomado por Cobros público u otra corrida: esperar y
# reintentar antes de pausar el lote (evita jobs muertos por contención breve).
PIPELINE_BUSY_RETRIES = 3
PIPELINE_BUSY_RETRY_SECONDS = 20
_IN_FLIGHT_CLASSIFY = ("en_proceso", "en_cola")
# Candado en-proceso: evita dos hilos advance del mismo scan (UI + scheduler).
_ADVANCE_LOCKS: Dict[int, threading.Lock] = {}
_ADVANCE_LOCKS_GUARD = threading.Lock()
# Señales de cancelación cooperativa (Detener desde UI).
_CANCEL_SCAN_IDS: set[int] = set()
_CANCEL_GUARD = threading.Lock()


def mailbox_target() -> str:
    return (
        getattr(settings, "GMAIL_MAILBOX", None)
        or "cobranza@rapicreditca.com"
    ).strip()


def _utcnow() -> datetime:
    return datetime.utcnow()


def _cobranza_tokens_path() -> str:
    return (
        getattr(settings, "GMAIL_TOKENS_PATH_COBRANZA", None) or "gmail_tokens_cobranza.json"
    ).strip()


def _cobranza_client_pair() -> Tuple[Optional[str], Optional[str]]:
    from app.services.pagos_gmail.credentials import get_cobranza_oauth_client_pair

    return get_cobranza_oauth_client_pair()


def cobranza_tokens_file_ready() -> bool:
    """Compat: True si hay refresh_token en archivo o BD."""
    return cobranza_tokens_ready()


def _gmail_service():
    from app.services.pagos_gmail.credentials import get_cobranza_gmail_credentials
    from app.services.pagos_gmail.gmail_service import build_gmail_service

    creds = get_cobranza_gmail_credentials()
    if creds is None:
        return None, None
    return build_gmail_service(creds), creds


def connection_status(db: Session) -> Dict[str, Any]:
    service, _ = _gmail_service()
    profile_email = None
    connected = False
    mode = "disconnected"
    err = None
    target = mailbox_target()
    mailbox_match: Optional[bool] = None
    if service is not None:
        try:
            prof = service.users().getProfile(userId="me").execute()
            profile_email = (prof.get("emailAddress") or "").strip() or None
            connected = True
            mode = "gmail"
            if profile_email and target:
                mailbox_match = profile_email.lower() == target.lower()
        except Exception as e:
            err = str(e)[:400]
            logger.warning("[AUDITORIA_EMAIL] perfil Gmail: %s", e)
    n_msg = int(
        db.execute(select(func.count()).select_from(AuditoriaEmailMessage)).scalar_one()
        or 0
    )
    n_rec = int(
        db.execute(select(func.count()).select_from(AuditoriaEmailReceipt)).scalar_one()
        or 0
    )
    ready = bool(connected and mailbox_match is not False)
    _, tokens_storage = load_cobranza_gmail_token_payload()
    return {
        "mailbox_target": target,
        "gmail_connected": connected,
        "gmail_profile_email": profile_email,
        "mailbox_match": mailbox_match,
        "ready_for_scan": ready and connected,
        "source_mode": mode,
        "tokens_path": _cobranza_tokens_path(),
        "tokens_file_ready": cobranza_tokens_file_ready(),
        "tokens_storage": tokens_storage,
        "label_analizados": analizados_label_name(),
        "error": err,
        "mensajes_bd": n_msg,
        "recibos_bd": n_rec,
        "manifest_version": MANIFEST_VERSION,
        "oauth_redirect_hint": (
            f"...{getattr(settings, 'API_V1_STR', '/api/v1')}/auditoria/email/oauth/callback"
        ),
        **cobranza_oauth_config_status(),
    }


def assert_ready_for_scan(db: Session) -> Dict[str, Any]:
    """Falla claro si no hay OAuth cobranza@ alineado al buzón objetivo."""
    st = connection_status(db)
    if not st.get("gmail_connected"):
        raise ValueError(
            f"Conecta {mailbox_target()} en Auditoría → Email → Conexión "
            "(OAuth con tokens separados de Pagos Gmail)."
        )
    if st.get("mailbox_match") is False:
        raise ValueError(
            f"El perfil OAuth es {st.get('gmail_profile_email')}, no {mailbox_target()}. "
            "Vuelve a autorizar entrando como esa casilla."
        )
    return st


def estimate(db: Session, criteria: Dict[str, Any]) -> Dict[str, Any]:
    _ = db
    c = apply_preset(criteria)
    q = build_gmail_query(c)
    service, _ = _gmail_service()
    if service is None:
        return {
            "source": "disconnected",
            "gmail_query": q,
            "estimated": 0,
            "exact": True,
            "mensaje": (
                "Gmail cobranza@ no conectado. Ve a Conexión y autoriza con "
                f"{mailbox_target()}."
            ),
        }
    try:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=q, maxResults=1, includeSpamTrash=False)
            .execute()
        )
        est = int(resp.get("resultSizeEstimate") or 0)
        return {
            "source": "gmail",
            "gmail_query": q,
            "estimated": est,
            "exact": False,
            "mensaje": "Estimación Gmail (aprox.). El post-filtro fuerte puede reducir el total.",
        }
    except Exception as e:
        logger.warning("[AUDITORIA_EMAIL] estimate: %s", e)
        return {
            "source": "error",
            "gmail_query": q,
            "estimated": 0,
            "exact": False,
            "error": str(e)[:300],
            "mensaje": "Fallo al consultar Gmail.",
        }


def _validate_create(mode: str, criteria: Dict[str, Any], lot_size: int, max_messages: int) -> None:
    mode = (mode or "single").strip().lower()
    if mode not in ("single", "batch"):
        raise ValueError("mode debe ser single o batch")
    if lot_size < 1 or lot_size > LOT_SIZE_MAX:
        raise ValueError(f"lotSize debe estar entre 1 y {LOT_SIZE_MAX}")
    if max_messages < 1 or max_messages > 32_000:
        raise ValueError("maxMessages debe estar entre 1 y 32000")
    if mode == "batch" and not has_date_bound(criteria):
        raise ValueError(
            "El modo batch exige dateFrom/dateTo o newerThanDays (tope ~32k)."
        )


def create_scan(
    db: Session,
    *,
    mode: str,
    criteria: Dict[str, Any],
    pipeline_ids: Optional[List[str]],
    lot_size: int,
    max_messages: int,
    created_by: Optional[str],
) -> AuditoriaEmailScan:
    mode = (mode or "single").strip().lower()
    c = apply_preset(criteria or {})
    max_messages = max(1, min(int(max_messages or LOT_SIZE_MAX), 32_000))
    if mode == "single":
        # Lote Gmail ≤100; el tope de mensajes puede ser mayor (avanza en lotes).
        lot_size = min(LOT_SIZE_MAX, max_messages)
    else:
        lot_size = max(1, min(int(lot_size or LOT_SIZE_MAX), LOT_SIZE_MAX))
    _validate_create(mode, c, lot_size, max_messages)
    assert_ready_for_scan(db)

    pids = pipeline_ids or ["pagos_gmail.vigente"]
    scan = AuditoriaEmailScan(
        mode=mode,
        status="paused",
        source="gmail",
        criteria_json=c,
        pipeline_ids_json=pids,
        lot_size=lot_size,
        max_messages=max_messages,
        gmail_query=build_gmail_query(c),
        page_token=None,
        processed_total=0,
        listed_total=0,
        rejected_total=0,
        lots_done=0,
        created_by=created_by,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def _header_map(payload: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for h in payload.get("headers") or []:
        name = str(h.get("name") or "").lower()
        if name:
            out[name] = str(h.get("value") or "")
    return out


def _parse_from(raw: str) -> Tuple[Optional[str], Optional[str]]:
    name, addr = parseaddr(raw or "")
    return (addr or None), (name or None)


def _walk_parts(part: Dict[str, Any], files: List[Tuple[str, int]]) -> None:
    filename = part.get("filename") or ""
    body = part.get("body") or {}
    size = int(body.get("size") or 0)
    if filename:
        files.append((str(filename), size))
    for child in part.get("parts") or []:
        _walk_parts(child, files)


def _gmail_message_to_row(
    service: Any,
    message_id: str,
    *,
    use_full: bool = False,
) -> Optional[Dict[str, Any]]:
    try:
        if use_full:
            full = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        else:
            full = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
    except Exception as e:
        logger.warning("[AUDITORIA_EMAIL] get message %s: %s", message_id, e)
        return None
    headers = _header_map(full.get("payload") or {})
    frm_email, frm_name = _parse_from(headers.get("from", ""))
    files: List[Tuple[str, int]] = []
    _walk_parts(full.get("payload") or {}, files)
    max_kb = max((sz // 1024 for _, sz in files), default=0) or None
    types = [fn for fn, _ in files]
    ms = int(full.get("internalDate") or 0)
    internal = datetime.utcfromtimestamp(ms / 1000.0) if ms else None
    label_ids = list(full.get("labelIds") or [])
    return {
        "gmail_message_id": message_id,
        "gmail_thread_id": full.get("threadId"),
        "from_email": frm_email,
        "from_name": frm_name,
        "subject": headers.get("subject"),
        "snippet": full.get("snippet"),
        "internal_date": internal,
        "has_attachment": bool(types) or ("ATTACHMENT" in label_ids),
        "attachment_types": types,
        "attachment_max_kb": max_kb,
        "filename_joined": "|".join(types),
        "label_ids": label_ids,
        "source": "gmail",
    }


def _upsert_tracking_message(
    db: Session,
    *,
    scan: AuditoriaEmailScan,
    raw: Dict[str, Any],
    classify: str,
    route: str,
    pipeline_status: str,
    pagos_sync_id: Optional[int],
    extract: Optional[Dict[str, Any]] = None,
) -> AuditoriaEmailMessage:
    mid = str(raw.get("gmail_message_id") or "").strip()
    existing = db.execute(
        select(AuditoriaEmailMessage).where(AuditoriaEmailMessage.gmail_message_id == mid)
    ).scalars().first()
    payload = {
        "pipelines": [
            {
                "id": "pagos_gmail.vigente",
                "status": pipeline_status,
                "pagos_sync_id": pagos_sync_id,
                "label": analizados_label_name(),
            }
        ],
        "pagos_sync_id": pagos_sync_id,
        "extract": extract or {},
    }
    if existing:
        existing.scan_id = scan.id
        existing.classify = classify
        existing.route = route
        existing.pipelines_json = payload
        existing.extract_json = extract or existing.extract_json
        existing.subject = raw.get("subject") or existing.subject
        existing.from_email = raw.get("from_email") or existing.from_email
        existing.from_name = raw.get("from_name") or existing.from_name
        existing.snippet = raw.get("snippet") or existing.snippet
        existing.has_attachment = bool(raw.get("has_attachment"))
        existing.attachment_types = list(raw.get("attachment_types") or [])
        existing.label_ids = list(raw.get("label_ids") or [])
        db.add(existing)
        msg = existing
    else:
        msg = AuditoriaEmailMessage(
            scan_id=scan.id,
            gmail_message_id=mid,
            gmail_thread_id=raw.get("gmail_thread_id"),
            source="gmail",
            from_email=raw.get("from_email"),
            from_name=raw.get("from_name"),
            subject=raw.get("subject"),
            snippet=raw.get("snippet"),
            internal_date=raw.get("internal_date"),
            has_attachment=bool(raw.get("has_attachment")),
            attachment_types=list(raw.get("attachment_types") or []),
            attachment_max_kb=raw.get("attachment_max_kb"),
            filename_joined=raw.get("filename_joined"),
            label_ids=list(raw.get("label_ids") or []),
            classify=classify,
            route=route,
            extract_json=extract,
            pipelines_json=payload,
            ingested_at=_utcnow(),
        )
        db.add(msg)
        db.flush()
    return msg


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        s = str(v).replace(",", ".").strip()
        # quitar símbolos no numéricos comunes
        cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
        return float(cleaned) if cleaned not in ("", "-", ".") else None
    except (TypeError, ValueError):
        return None


def _sync_item_outcomes(
    db: Session, sync_id: Optional[int], message_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Alinea tracking con filas del pipeline vigente (banco/cédula/monto)."""
    if not sync_id or not message_ids:
        return {}
    from app.models.pagos_gmail_sync import PagosGmailSyncItem

    rows = (
        db.execute(
            select(PagosGmailSyncItem).where(
                PagosGmailSyncItem.sync_id == sync_id,
                PagosGmailSyncItem.gmail_message_id.in_(message_ids),
            )
        )
        .scalars()
        .all()
    )
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        mid = str(r.gmail_message_id or "").strip()
        if not mid:
            continue
        prev = out.get(mid) or {"items": 0, "bancos": [], "cedulas": [], "montos": []}
        prev["items"] = int(prev["items"]) + 1
        if r.banco:
            prev["bancos"].append(str(r.banco))
        if r.cedula:
            prev["cedulas"].append(str(r.cedula))
        if r.monto:
            prev["montos"].append(str(r.monto))
        out[mid] = prev
    return out


def _classify_route_from_outcome(outcome: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not outcome or int(outcome.get("items") or 0) <= 0:
        return "sin_digitalizacion", "revision_o_omitido"
    bancos = outcome.get("bancos") or []
    banco = str(bancos[0]).upper() if bancos else "DIGITALIZADO"
    return banco, "digitalizado"


def _release_in_flight_for_scan(
    db: Session,
    scan_id: int,
    *,
    classify: str = "pausado",
    route: str = "pendiente_reintento",
) -> int:
    """Pasa en_cola/en_proceso → pausado (lote interrumpido o worker caído)."""
    rows = (
        db.execute(
            select(AuditoriaEmailMessage).where(
                AuditoriaEmailMessage.scan_id == scan_id,
                AuditoriaEmailMessage.classify.in_(_IN_FLIGHT_CLASSIFY),
            )
        )
        .scalars()
        .all()
    )
    for msg in rows:
        msg.classify = classify
        msg.route = route
        pipe = dict(msg.pipelines_json or {})
        pipe["status_note"] = "liberado_in_flight"
        msg.pipelines_json = pipe
        db.add(msg)
    return len(rows)


def release_stale_in_flight_messages(db: Session) -> int:
    """
    Libera filas en_proceso/en_cola si su escaneo ya no está activo.
    Evita Bandeja eternamente en «En proceso» tras pause/crash.
    """
    scan_ids = (
        db.execute(
            select(AuditoriaEmailMessage.scan_id)
            .where(AuditoriaEmailMessage.classify.in_(_IN_FLIGHT_CLASSIFY))
            .distinct()
        )
        .scalars()
        .all()
    )
    if not scan_ids:
        return 0
    released = 0
    for sid in scan_ids:
        if sid is None:
            continue
        scan = db.get(AuditoriaEmailScan, int(sid))
        if scan is None:
            released += _release_in_flight_for_scan(db, int(sid))
            continue
        active = scan.status == "running" and not _scan_looks_stale_running(scan)
        if active:
            continue
        released += _release_in_flight_for_scan(db, int(sid))
    if released:
        db.commit()
        logger.info(
            "[AUDITORIA_EMAIL] liberados %d mensajes in-flight (scan idle/stale)",
            released,
        )
    return released


def normalize_active_lot_display(db: Session) -> int:
    """
    Con escaneo activo: como máximo 1 «en_proceso»; el resto → «en_cola».
    Corrige lotes viejos que marcaban los 50 a la vez.
    """
    scan_ids = (
        db.execute(
            select(AuditoriaEmailMessage.scan_id)
            .where(AuditoriaEmailMessage.classify == "en_proceso")
            .distinct()
        )
        .scalars()
        .all()
    )
    if not scan_ids:
        return 0
    fixed = 0
    for sid in scan_ids:
        if sid is None:
            continue
        scan = db.get(AuditoriaEmailScan, int(sid))
        if scan is None:
            continue
        if scan.status != "running" or _scan_looks_stale_running(scan):
            continue
        rows = (
            db.execute(
                select(AuditoriaEmailMessage)
                .where(
                    AuditoriaEmailMessage.scan_id == int(sid),
                    AuditoriaEmailMessage.classify == "en_proceso",
                )
                .order_by(desc(AuditoriaEmailMessage.id))
            )
            .scalars()
            .all()
        )
        if len(rows) <= 1:
            continue
        # Conserva el más reciente como en_proceso; demota el resto.
        for msg in rows[1:]:
            msg.classify = "en_cola"
            msg.route = "en_cola"
            pipe = dict(msg.pipelines_json or {})
            pipe["status_note"] = "demoted_to_en_cola"
            msg.pipelines_json = pipe
            db.add(msg)
            fixed += 1
    if fixed:
        db.commit()
        logger.info(
            "[AUDITORIA_EMAIL] demoted %d en_proceso → en_cola (lote activo)",
            fixed,
        )
    return fixed


def _post_pipeline_cola_recibos(
    db: Session,
    pipe_status: str,
    *,
    sync_id: Optional[int] = None,
    candidate_message_ids: Optional[List[str]] = None,
    message_db_by_gmail: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Digitalización → materializar cola Recibos (sin auto-conciliar ni anti-limbo alta)."""
    if pipe_status == "no_credentials":
        return {
            "skipped": True,
            "reason": pipe_status,
            "analizados": {"listos": [], "pendientes_temporal": list(candidate_message_ids or [])},
            "materializar": {"creados": 0, "actualizados": 0, "listos_analizados": []},
        }
    try:
        from app.services.auditoria_email.receipts_service import (
            materializar_recibos_desde_sync,
        )

        mat = materializar_recibos_desde_sync(
            db,
            sync_id=sync_id,
            message_ids=list(candidate_message_ids or []),
            message_db_by_gmail=message_db_by_gmail,
        )
        listos = list(mat.get("listos_analizados") or [])
        logger.info(
            "[AUDITORIA_EMAIL] cola recibos sync=%s status=%s → %s",
            sync_id,
            pipe_status,
            mat,
        )
        return {
            "materializar": mat,
            "analizados": {
                "listos": listos,
                "pendientes_temporal": [
                    m
                    for m in (candidate_message_ids or [])
                    if m not in set(listos)
                ],
            },
        }
    except Exception as e:
        logger.warning("[AUDITORIA_EMAIL] materializar recibos falló: %s", e)
        return {
            "error": str(e)[:300],
            "analizados": {
                "listos": [],
                "pendientes_temporal": list(candidate_message_ids or []),
            },
            "materializar": {"creados": 0, "actualizados": 0, "listos_analizados": []},
        }


_GMAIL_SYSTEM_LABELS = frozenset(
    {
        "INBOX",
        "UNREAD",
        "STARRED",
        "IMPORTANT",
        "SENT",
        "DRAFT",
        "SPAM",
        "TRASH",
        "CATEGORY_PERSONAL",
        "CATEGORY_UPDATES",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_SOCIAL",
        "CATEGORY_FORUMS",
    }
)


def _has_user_labels(label_ids: Optional[List[Any]]) -> bool:
    """True si el mensaje tiene alguna etiqueta de usuario (banco, ANALIZADOS, etc.)."""
    for lid in label_ids or []:
        s = str(lid or "").strip()
        if not s:
            continue
        if s in _GMAIL_SYSTEM_LABELS or s.startswith("CATEGORY_"):
            continue
        return True
    return False


def _targets_analizados_adicional(
    *,
    gmail_message_id: str,
    listos: List[str],
    label_ids: Optional[List[Any]] = None,
    digitalizado: bool = False,
    force_skip: bool = False,
) -> List[str]:
    """
    Destinos para ANALIZADOS como etiqueta adicional (no sustituye MERCANTIL/BNC/…).

    - Con recibo materializado (listos)
    - O si ya tenía / tiene etiqueta de usuario
    - O si el pipeline digitalizó (suele aplicar etiqueta de banco)

    ``force_skip``: omitido por sin préstamo APROBADO → no etiquetar (puede reingresar).
    """
    mid = str(gmail_message_id or "").strip()
    if not mid or force_skip:
        return []
    out: List[str] = []
    if mid in set(listos) or _has_user_labels(label_ids) or digitalizado:
        out.append(mid)
    return out


def _apply_analizados(service: Any, message_ids: List[str]) -> int:
    """
    Añade ANALIZADOS sin quitar etiquetas existentes (MERCANTIL, BNC, BINANCE, …).
    Usa solo ``addLabelIds``.
    """
    from app.services.pagos_gmail.gmail_service import (
        add_message_user_labels_only,
        ensure_user_label_id,
    )

    label = analizados_label_name()
    lid = ensure_user_label_id(service, label)
    if not lid:
        logger.warning("[AUDITORIA_EMAIL] No se pudo asegurar etiqueta %s", label)
        return 0
    ok = 0
    for mid in dict.fromkeys(str(m) for m in message_ids if m):
        try:
            add_message_user_labels_only(service, mid, [lid])
            ok += 1
        except Exception as e:
            logger.warning("[AUDITORIA_EMAIL] ANALIZADOS msg=%s: %s", mid, e)
    return ok


def _run_pagos_pipeline_lot(
    db: Session,
    *,
    message_ids: List[str],
    creds: Any,
) -> Tuple[Optional[int], str]:
    from app.services.pagos_gmail.pipeline import run_pipeline
    from app.services.pagos_gmail.sync_stale import (
        GmailPipelineBusyError,
        reserve_gmail_pipeline_sync,
    )

    if not message_ids:
        return None, "success"
    # Cobros público / Pagos Gmail toman el lock por segundos: esperar en vez de
    # abortar el lote deja el escaneo avanzando sin intervención manual.
    sync = None
    last_busy: Optional[BaseException] = None
    for intento in range(1, PIPELINE_BUSY_RETRIES + 1):
        try:
            sync = reserve_gmail_pipeline_sync(db, force=True)
            break
        except GmailPipelineBusyError as e:
            last_busy = e
            if intento >= PIPELINE_BUSY_RETRIES:
                break
            logger.info(
                "[AUDITORIA_EMAIL] pipeline ocupado; reintento %s/%s en %ss",
                intento,
                PIPELINE_BUSY_RETRIES,
                PIPELINE_BUSY_RETRY_SECONDS,
            )
            db.rollback()
            time.sleep(PIPELINE_BUSY_RETRY_SECONDS)
    if sync is None:
        raise RuntimeError(
            "El pipeline Pagos Gmail está ocupado (otra corrida en curso). "
            "Reintenta este lote en unos minutos."
        ) from last_busy
    sync_id, status = run_pipeline(
        db,
        existing_sync_id=sync.id,
        only_message_ids=list(message_ids),
        gmail_credentials=creds,
        defer_autoconciliacion=True,
    )
    return sync_id, status


def _heartbeat_scan(db: Session, scan: AuditoriaEmailScan, *, note: str = "") -> None:
    """Latido en BD para que GET no marque huérfano durante list/fetch Gmail."""
    if _stop_requested(db, int(scan.id)):
        return
    scan.updated_at = _utcnow()
    if scan.status != "paused":
        scan.status = "running"
    db.add(scan)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(
            "[AUDITORIA_EMAIL] heartbeat falló scan=%s %s", scan.id, note or ""
        )


def _advance_gmail(db: Session, scan: AuditoriaEmailScan, max_lots: int) -> Dict[str, Any]:
    service, creds = _gmail_service()
    if service is None or creds is None:
        scan.last_error = f"Sin credenciales cobranza@ ({mailbox_target()})"
        scan.status = "paused"
        scan.updated_at = _utcnow()
        db.add(scan)
        db.commit()
        raise RuntimeError(scan.last_error)

    criteria = dict(scan.criteria_json or {})
    q = scan.gmail_query or build_gmail_query(criteria)
    use_full = criteria_needs_payload_inspection(criteria)
    page_token = scan.page_token
    lots = 0
    logger.info(
        "[AUDITORIA_EMAIL] advance start scan=%s lots=%s q=%s",
        scan.id,
        max_lots,
        (q or "")[:240],
    )
    _heartbeat_scan(db, scan, note="advance_start")

    while lots < max_lots and int(scan.processed_total or 0) < int(scan.max_messages or 0):
        if _stop_requested(db, int(scan.id)):
            return _apply_user_stop(db, scan, page_token=page_token)
        remaining = int(scan.max_messages) - int(scan.processed_total or 0)
        page_size = min(LOT_SIZE_MAX, int(scan.lot_size or LOT_SIZE_MAX), remaining)
        if page_size <= 0:
            break
        # Pedir un poco más si hay post-filtro local estricto (min KB / filename).
        list_size = page_size if not use_full else min(LOT_SIZE_MAX, page_size * 2)
        params: Dict[str, Any] = {
            "userId": "me",
            "q": q,
            "maxResults": list_size,
            "includeSpamTrash": False,
        }
        if page_token:
            params["pageToken"] = page_token
        logger.info(
            "[AUDITORIA_EMAIL] list start scan=%s q=%s maxResults=%s page_token=%s",
            scan.id,
            (q or "")[:240],
            list_size,
            bool(page_token),
        )
        _heartbeat_scan(db, scan, note="pre_list")
        if _stop_requested(db, int(scan.id)):
            return _apply_user_stop(db, scan, page_token=page_token)
        try:
            resp = service.users().messages().list(**params).execute()
        except Exception as e:
            scan.last_error = str(e)[:1000]
            scan.status = "paused"
            scan.updated_at = _utcnow()
            db.add(scan)
            db.commit()
            raise

        refs = resp.get("messages") or []
        next_token = resp.get("nextPageToken")
        logger.info(
            "[AUDITORIA_EMAIL] list ok scan=%s refs=%s next_page=%s",
            scan.id,
            len(refs),
            bool(next_token),
        )
        _heartbeat_scan(db, scan, note="post_list")
        accepted_rows: List[Dict[str, Any]] = []
        listed = 0
        rejected = 0

        for ref in refs:
            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=page_token)
            mid = ref.get("id")
            if not mid:
                continue
            listed += 1
            # Latido cada 5 mensajes: evita heal huérfano en «Preparando lote»
            # aunque el filtro local rechace casi todos.
            if listed % 5 == 0:
                _heartbeat_scan(db, scan, note=f"fetch_{listed}")
            raw = _gmail_message_to_row(service, mid, use_full=use_full)
            if raw is None:
                rejected += 1
                continue
            if not matches_criteria(
                raw, criteria, trust_gmail_attachment_q=not use_full
            ):
                rejected += 1
                continue
            accepted_rows.append(raw)
            if len(accepted_rows) >= page_size:
                break

        scan.listed_total = int(scan.listed_total or 0) + listed
        scan.rejected_total = int(scan.rejected_total or 0) + rejected
        # Persistir listados aunque el lote aún no pase a OCR (UI dejaba 0).
        scan.updated_at = _utcnow()
        if scan.status != "paused":
            scan.status = "running"
        db.add(scan)
        db.commit()
        logger.info(
            "[AUDITORIA_EMAIL] lote filtrado scan=%s listed=%s accepted=%s rejected=%s",
            scan.id,
            listed,
            len(accepted_rows),
            rejected,
        )

        if accepted_rows:
            # 1) Lote visible en Bandeja como «en_cola» (solo el actual pasa a en_proceso).
            msg_db_map: Dict[str, int] = {}
            for raw in accepted_rows:
                mid = str(raw["gmail_message_id"])
                msg = _upsert_tracking_message(
                    db,
                    scan=scan,
                    raw=raw,
                    classify="en_cola",
                    route="en_cola",
                    pipeline_status="queued",
                    pagos_sync_id=None,
                    extract=None,
                )
                if msg and msg.id:
                    msg_db_map[mid] = int(msg.id)
            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=page_token)
            scan.status = "running"
            scan.updated_at = _utcnow()
            db.add(scan)
            db.commit()

            # 2) OCR de a uno: actualiza Bandeja/Recibos tras cada correo.
            for raw in accepted_rows:
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                mid = str(raw["gmail_message_id"])
                _upsert_tracking_message(
                    db,
                    scan=scan,
                    raw=raw,
                    classify="en_proceso",
                    route="escaneando",
                    pipeline_status="running",
                    pagos_sync_id=None,
                    extract=None,
                )
                # No pisar un Detener concurrente.
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                scan.updated_at = _utcnow()
                # Conservar paused si Detener ganó la carrera de escritura.
                if scan.status != "paused":
                    scan.status = "running"
                db.add(scan)
                db.commit()
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                try:
                    sync_id, pipe_status = _run_pagos_pipeline_lot(
                        db, message_ids=[mid], creds=creds
                    )
                except Exception as e:
                    if _stop_requested(db, int(scan.id)):
                        return _apply_user_stop(db, scan, page_token=page_token)
                    scan.last_error = str(e)[:1000]
                    scan.status = "paused"
                    scan.page_token = page_token
                    scan.updated_at = _utcnow()
                    if _pipeline_busy_error(e):
                        # No quemar el correo: reintento cuando Pagos Gmail libere el lock.
                        _upsert_tracking_message(
                            db,
                            scan=scan,
                            raw=raw,
                            classify="pausado",
                            route="pendiente_reintento",
                            pipeline_status="busy",
                            pagos_sync_id=None,
                            extract={"error": str(e)[:300], "retry": True},
                        )
                    else:
                        _upsert_tracking_message(
                            db,
                            scan=scan,
                            raw=raw,
                            classify="error_pipeline",
                            route="revision_o_omitido",
                            pipeline_status="error",
                            pagos_sync_id=None,
                            extract={"error": str(e)[:300]},
                        )
                    # Resto del lote: dejar de mostrar «En proceso» / «En cola».
                    _release_in_flight_for_scan(db, int(scan.id))
                    db.add(scan)
                    db.commit()
                    raise

                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                outcomes = _sync_item_outcomes(db, sync_id, [mid])
                oc = outcomes.get(mid)
                classify, route = _classify_route_from_outcome(oc)
                extract = None
                if oc:
                    extract = {
                        "banco": (oc.get("bancos") or [None])[0],
                        "cedula": (oc.get("cedulas") or [None])[0],
                        "monto": (oc.get("montos") or [None])[0],
                        "items": oc.get("items"),
                        "pagos_sync_id": sync_id,
                    }
                msg = _upsert_tracking_message(
                    db,
                    scan=scan,
                    raw=raw,
                    classify=classify or "digitalizado",
                    route=route or "pendiente_aprobacion",
                    pipeline_status=pipe_status,
                    pagos_sync_id=sync_id,
                    extract=extract,
                )
                if msg and msg.id:
                    msg_db_map[mid] = int(msg.id)
                db.flush()

                mig = _post_pipeline_cola_recibos(
                    db,
                    pipe_status,
                    sync_id=sync_id,
                    candidate_message_ids=[mid],
                    message_db_by_gmail={mid: msg_db_map[mid]}
                    if mid in msg_db_map
                    else msg_db_map,
                )
                listos = list((mig.get("analizados") or {}).get("listos") or [])
                omitidos = list(
                    (mig.get("materializar") or {}).get("omitidos_no_aprobado") or []
                )
                digitalizado = bool(oc and int(oc.get("items") or 0) > 0)
                # No ANALIZADOS si se omitió por cédula sin préstamo APROBADO
                # (puede reingresar cuando el crédito se apruebe).
                if mid in omitidos:
                    digitalizado_for_label = False
                    listos_for_label: List[str] = []
                else:
                    digitalizado_for_label = digitalizado
                    listos_for_label = listos
                targets = _targets_analizados_adicional(
                    gmail_message_id=mid,
                    listos=listos_for_label,
                    label_ids=list(raw.get("label_ids") or []),
                    digitalizado=digitalizado_for_label,
                    force_skip=mid in omitidos,
                )
                # ANALIZADOS adicional: no reemplaza etiqueta de banco existente.
                labeled = _apply_analizados(service, targets) if targets else 0
                if not targets:
                    logger.info(
                        "[AUDITORIA_EMAIL] sin ANALIZADOS (sin recibo ni etiqueta): "
                        "msg=%s scan=%s",
                        mid,
                        scan.id,
                    )
                logger.info(
                    "[AUDITORIA_EMAIL] msg scan=%s sync=%s status=%s mid=%s "
                    "ANALIZADOS=%d (adicional) cola_recibos=%s",
                    scan.id,
                    sync_id,
                    pipe_status,
                    mid,
                    labeled,
                    mig.get("materializar") or {},
                )
                scan.processed_total = int(scan.processed_total or 0) + 1
                scan.updated_at = _utcnow()
                db.add(scan)
                db.commit()
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
        elif refs and not next_token:
            # Página final sin aceptados → fin limpio.
            pass
        elif refs and next_token and listed > 0 and len(accepted_rows) == 0:
            # Página con solo rechazos locales: avanzar cursor para no ciclar.
            logger.info(
                "[AUDITORIA_EMAIL] scan=%s página sin aceptados (listed=%d rejected=%d); avanza token",
                scan.id,
                listed,
                rejected,
            )

        scan.lots_done = int(scan.lots_done or 0) + 1
        lots += 1
        page_token = next_token

        hit_cap = int(scan.processed_total or 0) >= int(scan.max_messages or 0)
        no_more = not next_token or not refs
        if hit_cap or no_more:
            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=None if hit_cap or no_more else page_token)
            scan.page_token = None
            scan.status = "complete"
            scan.finished_at = _utcnow()
            scan.last_error = None
            break
        if _stop_requested(db, int(scan.id)):
            return _apply_user_stop(db, scan, page_token=next_token)
        scan.page_token = next_token
        scan.status = "paused"
        # No borrar «Detenido por el usuario» si el stop llegó en paralelo.
        if not _user_stopped_scan(scan):
            scan.last_error = None

    if _stop_requested(db, int(scan.id)) or _user_stopped_scan(scan):
        return _apply_user_stop(db, scan, page_token=scan.page_token)
    scan.updated_at = _utcnow()
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return _scan_dict(scan)


def _scan_looks_stale_running(scan: AuditoriaEmailScan) -> bool:
    if scan.status != "running":
        return False
    ts = scan.updated_at or scan.created_at
    if not ts:
        return True
    age = (_utcnow() - ts).total_seconds() / 60.0
    return age >= SCAN_STALE_RUNNING_MINUTES


def _scan_looks_orphaned_running(scan: AuditoriaEmailScan, db: Optional[Session] = None) -> bool:
    """
    running en BD sin hilo local (lock libre) y sin latido reciente.
    Tras deploy/crash el front seguía mostrando «Escaneando…» eternamente.

    No usar umbral corto con inflight=0: en «Preparando lote» (list/fetch Gmail)
    aún no hay en_cola/en_proceso y un heal a los 45s mata el worker legítimo
    si el candado en memoria ya no está (deploy, race, otro proceso).
    """
    if scan.status != "running":
        return False
    lock = _advance_lock_for(int(scan.id))
    if lock.locked():
        return False
    ts = scan.updated_at or scan.created_at
    if not ts:
        return True
    age_min = (_utcnow() - ts).total_seconds() / 60.0
    return age_min >= SCAN_ORPHAN_RUNNING_MINUTES


def _request_cancel_scan(scan_id: int) -> None:
    with _CANCEL_GUARD:
        _CANCEL_SCAN_IDS.add(int(scan_id))


def _clear_cancel_scan(scan_id: int) -> None:
    with _CANCEL_GUARD:
        _CANCEL_SCAN_IDS.discard(int(scan_id))


def _cancel_requested(scan_id: int) -> bool:
    with _CANCEL_GUARD:
        return int(scan_id) in _CANCEL_SCAN_IDS


def _user_stopped_scan(scan: AuditoriaEmailScan) -> bool:
    if (scan.last_error or "").strip().lower().startswith("detenido"):
        return True
    crit = scan.criteria_json if isinstance(scan.criteria_json, dict) else {}
    return bool(crit.get("user_stopped"))


def _stop_requested(db: Session, scan_id: int) -> bool:
    """True si Detener (memoria) o BD ya quedó paused/user_stopped."""
    if _cancel_requested(scan_id):
        return True
    row = db.get(AuditoriaEmailScan, int(scan_id))
    if row is None:
        return True
    try:
        db.refresh(row)
    except Exception:
        pass
    if _user_stopped_scan(row):
        return True
    # pause_scan ya escribió paused + Detenido; el hilo no debe volver a running.
    if row.status == "paused" and _cancel_requested(scan_id):
        return True
    return False


def _apply_user_stop(
    db: Session,
    scan: AuditoriaEmailScan,
    *,
    page_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Deja el escaneo detenido de forma estable (BD + in-flight)."""
    if page_token is not None:
        scan.page_token = page_token
    scan.status = "paused"
    scan.last_error = "Detenido por el usuario"
    scan.updated_at = _utcnow()
    crit = dict(scan.criteria_json or {}) if isinstance(scan.criteria_json, dict) else {}
    crit["user_stopped"] = True
    scan.criteria_json = crit
    _release_in_flight_for_scan(db, int(scan.id))
    db.add(scan)
    db.commit()
    db.refresh(scan)
    # Mantener flag en memoria hasta Reanudar: el hilo OCR lo consulta tras el correo actual.
    logger.info(
        "[AUDITORIA_EMAIL] scan=%s DETENIDO processed=%s page_token=%s",
        scan.id,
        scan.processed_total,
        bool(scan.page_token),
    )
    out = _scan_dict(scan)
    out["stopped"] = True
    return out


def _clear_user_stop_flag(scan: AuditoriaEmailScan) -> None:
    crit = dict(scan.criteria_json or {}) if isinstance(scan.criteria_json, dict) else {}
    if "user_stopped" in crit:
        crit.pop("user_stopped", None)
        scan.criteria_json = crit
    if (scan.last_error or "").strip().lower().startswith("detenido"):
        scan.last_error = None


def _advance_lock_for(scan_id: int) -> threading.Lock:
    with _ADVANCE_LOCKS_GUARD:
        lock = _ADVANCE_LOCKS.get(scan_id)
        if lock is None:
            lock = threading.Lock()
            _ADVANCE_LOCKS[scan_id] = lock
        return lock


def _pipeline_busy_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if "GmailPipelineBusy" in name:
        return True
    msg = str(exc).lower()
    return "ocupado" in msg or "pipeline busy" in msg or "gmailpipelinebusy" in msg


def _advance_gmail_background(scan_id: int, max_lots: int) -> None:
    from app.core.database import SessionLocal

    lock = _advance_lock_for(scan_id)
    if not lock.acquire(blocking=False):
        logger.info(
            "[AUDITORIA_EMAIL] advance ya en curso (skip hilo) scan=%s", scan_id
        )
        return
    db = SessionLocal()
    try:
        scan = db.get(AuditoriaEmailScan, scan_id)
        if scan is None:
            return
        _advance_gmail(db, scan, max_lots)
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] background advance scan=%s: %s", scan_id, e)
        try:
            scan = db.get(AuditoriaEmailScan, scan_id)
            if scan and scan.status == "running":
                scan.status = "paused"
                scan.last_error = str(e)[:1000]
                scan.updated_at = _utcnow()
                db.add(scan)
                _release_in_flight_for_scan(db, scan_id)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
        lock.release()


def advance_scan(
    db: Session,
    scan_id: int,
    *,
    max_lots: int = 1,
    background: bool = True,
) -> Dict[str, Any]:
    """
    Avanza lotes del escaneo. Por defecto en hilo (evita timeout HTTP con OCR).
    ``max_lots`` se limita a 3 para no saturar; la UI puede reanudar en bucle.
    """
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if scan.status == "complete":
        return _scan_dict(scan)

    # Candado en-proceso: UI auto-reanudar + scheduler no lanzan 2 hilos.
    lock = _advance_lock_for(scan_id)
    if lock.locked() and scan.status == "running" and not _scan_looks_stale_running(scan):
        out = _scan_dict(scan)
        out["alreadyRunning"] = True
        return out

    if scan.status == "running" and (
        _scan_looks_stale_running(scan) or _scan_looks_orphaned_running(scan, db)
    ):
        scan.status = "paused"
        scan.last_error = (
            scan.last_error
            or (
                f"Reanudable: corrida previa sin latido >{SCAN_STALE_RUNNING_MINUTES} min"
                if _scan_looks_stale_running(scan)
                else f"Worker OCR detenido (sin latido >{SCAN_ORPHAN_RUNNING_MINUTES} min)"
            )
        )
        _release_in_flight_for_scan(db, int(scan.id))
        db.add(scan)
        db.commit()
        db.refresh(scan)
    elif scan.status == "running":
        out = _scan_dict(scan)
        out["alreadyRunning"] = True
        return out

    assert_ready_for_scan(db)
    _clear_cancel_scan(scan_id)
    _clear_user_stop_flag(scan)
    max_lots = max(1, min(int(max_lots or 1), 3))
    scan.status = "running"
    scan.updated_at = _utcnow()
    db.add(scan)
    db.commit()
    db.refresh(scan)

    if background:
        threading.Thread(
            target=_advance_gmail_background,
            args=(scan_id, max_lots),
            name=f"auditoria-email-scan-{scan_id}",
            daemon=True,
        ).start()
        return _scan_dict(scan)
    if not lock.acquire(blocking=False):
        out = _scan_dict(scan)
        out["alreadyRunning"] = True
        return out
    try:
        return _advance_gmail(db, scan, max_lots)
    finally:
        lock.release()


def pause_scan(db: Session, scan_id: int) -> Dict[str, Any]:
    """Detiene el escaneo: marca cancelación, libera in-flight y deja paused."""
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if scan.status == "complete":
        return _scan_dict(scan)

    _request_cancel_scan(int(scan_id))
    return _apply_user_stop(db, scan, page_token=scan.page_token)


def heal_orphaned_scan(db: Session, scan_id: int) -> Dict[str, Any]:
    """Si GET ve running huérfano, pausa para que el front deje de mentir."""
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if _scan_looks_orphaned_running(scan, db) or _scan_looks_stale_running(scan):
        scan.status = "paused"
        scan.last_error = (
            scan.last_error
            or f"Worker OCR detenido (sin latido >{SCAN_ORPHAN_RUNNING_MINUTES} min)"
        )
        scan.updated_at = _utcnow()
        _release_in_flight_for_scan(db, int(scan_id))
        db.add(scan)
        db.commit()
        db.refresh(scan)
        logger.info("[AUDITORIA_EMAIL] heal orphan scan=%s → paused", scan_id)
    return _scan_dict(scan)


def auto_advance_paused_scans(
    db: Session,
    *,
    max_scans: int = 1,
    max_lots: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Reanuda escaneos ``paused`` (cola batch sin navegador).
    Usado por el scheduler cuando ``AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED``.

    Incluye los pausados **sin** ``page_token``: un job cuyo primer lote falló
    (pipeline ocupado, error Gmail, heal huérfano) nunca llegó a fijar cursor y
    antes quedaba muerto hasta que alguien pulsara Reanudar.
    """
    lots = max_lots
    if lots is None:
        lots = int(getattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_MAX_LOTS", 2) or 2)
    lots = max(1, min(int(lots), 3))
    max_scans = max(1, min(int(max_scans or 1), 3))

    try:
        assert_ready_for_scan(db)
    except ValueError as e:
        return {"ok": False, "reason": str(e)[:300], "advanced": []}

    # Prioridad: con cursor (mitad de camino) antes que los que nunca arrancaron.
    rows = (
        db.execute(
            select(AuditoriaEmailScan)
            .where(
                AuditoriaEmailScan.status == "paused",
                AuditoriaEmailScan.page_token.isnot(None),
            )
            .order_by(AuditoriaEmailScan.id.asc())
            .limit(max_scans)
        )
        .scalars()
        .all()
    )
    if len(rows) < max_scans:
        sin_cursor = (
            db.execute(
                select(AuditoriaEmailScan)
                .where(
                    AuditoriaEmailScan.status == "paused",
                    AuditoriaEmailScan.page_token.is_(None),
                    AuditoriaEmailScan.finished_at.is_(None),
                )
                .order_by(desc(AuditoriaEmailScan.id))
                .limit(max_scans)
            )
            .scalars()
            .all()
        )
        vistos = {r.id for r in rows}
        for s in sin_cursor:
            if s.id in vistos:
                continue
            if int(s.processed_total or 0) >= int(s.max_messages or 0):
                continue
            rows.append(s)
            if len(rows) >= max_scans:
                break
    # También reanudar running stale (worker caído).
    if len(rows) < max_scans:
        stale = (
            db.execute(
                select(AuditoriaEmailScan)
                .where(AuditoriaEmailScan.status == "running")
                .order_by(AuditoriaEmailScan.id.asc())
                .limit(max_scans)
            )
            .scalars()
            .all()
        )
        for s in stale:
            if _scan_looks_stale_running(s) and s.id not in {r.id for r in rows}:
                rows.append(s)
            if len(rows) >= max_scans:
                break

    advanced: List[Dict[str, Any]] = []
    for scan in rows:
        if _user_stopped_scan(scan):
            logger.info(
                "[AUDITORIA_EMAIL] auto-avance omite scan=%s (Detenido por el usuario)",
                scan.id,
            )
            advanced.append({"scan_id": scan.id, "skipped": "user_stopped"})
            continue
        try:
            out = advance_scan(db, int(scan.id), max_lots=lots, background=True)
            advanced.append({"scan_id": scan.id, "status": out.get("status")})
        except Exception as e:
            logger.warning(
                "[AUDITORIA_EMAIL] auto-avance scan=%s: %s", scan.id, e
            )
            advanced.append({"scan_id": scan.id, "error": str(e)[:200]})
    return {"ok": True, "advanced": advanced, "max_lots": lots}


def _scan_dict(scan: AuditoriaEmailScan) -> Dict[str, Any]:
    return {
        "id": scan.id,
        "mode": scan.mode,
        "status": scan.status,
        "source": scan.source,
        "criteria": scan.criteria_json,
        "pipelineIds": scan.pipeline_ids_json,
        "lotSize": scan.lot_size,
        "maxMessages": scan.max_messages,
        "gmailQuery": scan.gmail_query,
        "pageToken": scan.page_token,
        "processedTotal": scan.processed_total,
        "listedTotal": scan.listed_total,
        "rejectedTotal": scan.rejected_total,
        "lotsDone": scan.lots_done,
        "lastError": scan.last_error,
        "createdBy": scan.created_by,
        "createdAt": scan.created_at.isoformat() if scan.created_at else None,
        "updatedAt": scan.updated_at.isoformat() if scan.updated_at else None,
        "finishedAt": scan.finished_at.isoformat() if scan.finished_at else None,
        "paused": (
            scan.status == "paused"
            and (
                bool(scan.page_token)
                # Job recién creado: sin pageToken aún, pero hay que arrancar el 1.er lote.
                or (
                    int(scan.processed_total or 0) == 0
                    and int(scan.lots_done or 0) == 0
                    and scan.finished_at is None
                )
                or _user_stopped_scan(scan)
            )
        ),
        "stopped": _user_stopped_scan(scan),
        "labelAnalizados": analizados_label_name(),
    }


def get_scan(db: Session, scan_id: int) -> Dict[str, Any]:
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if scan.status == "running" and (
        _scan_looks_orphaned_running(scan, db) or _scan_looks_stale_running(scan)
    ):
        return heal_orphaned_scan(db, scan_id)
    return _scan_dict(scan)


def list_paused_scans(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    rows = (
        db.execute(
            select(AuditoriaEmailScan)
            .where(AuditoriaEmailScan.status == "paused")
            .order_by(desc(AuditoriaEmailScan.id))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_scan_dict(r) for r in rows]


def list_bitacora(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = (
        db.execute(
            select(AuditoriaEmailScan).order_by(desc(AuditoriaEmailScan.id)).limit(limit)
        )
        .scalars()
        .all()
    )
    return [_scan_dict(r) for r in rows]


def kpis(db: Session) -> Dict[str, Any]:
    n_msg = int(
        db.execute(select(func.count()).select_from(AuditoriaEmailMessage)).scalar_one()
        or 0
    )
    n_rec = int(
        db.execute(select(func.count()).select_from(AuditoriaEmailReceipt)).scalar_one()
        or 0
    )
    n_rec_pending = int(
        db.execute(
            select(func.count())
            .select_from(AuditoriaEmailReceipt)
            .where(AuditoriaEmailReceipt.status == "pending")
        ).scalar_one()
        or 0
    )
    by_route = dict(
        db.execute(
            select(AuditoriaEmailMessage.route, func.count())
            .group_by(AuditoriaEmailMessage.route)
        ).all()
    )
    by_class = dict(
        db.execute(
            select(AuditoriaEmailMessage.classify, func.count())
            .group_by(AuditoriaEmailMessage.classify)
        ).all()
    )
    paused = int(
        db.execute(
            select(func.count())
            .select_from(AuditoriaEmailScan)
            .where(AuditoriaEmailScan.status == "paused")
        ).scalar_one()
        or 0
    )
    current_row = (
        db.execute(
            select(AuditoriaEmailMessage)
            .where(AuditoriaEmailMessage.classify == "en_proceso")
            .order_by(desc(AuditoriaEmailMessage.id))
            .limit(1)
        )
        .scalars()
        .first()
    )
    current_msg: Optional[Dict[str, Any]] = None
    if current_row is not None:
        current_msg = {
            "id": current_row.id,
            "gmailMessageId": current_row.gmail_message_id,
            "subject": (current_row.subject or "")[:120],
            "fromEmail": current_row.from_email,
            "scanId": current_row.scan_id,
        }
    return {
        "mensajes": n_msg,
        "recibos": n_rec,
        "recibos_pending": n_rec_pending,
        "por_ruta": {str(k or "sin_ruta"): int(v) for k, v in by_route.items()},
        "por_clase": {str(k or "sin_clase"): int(v) for k, v in by_class.items()},
        "en_proceso": int(by_class.get("en_proceso") or 0),
        "en_cola": int(by_class.get("en_cola") or 0),
        "pausado": int(by_class.get("pausado") or 0),
        "escaneos_pausados": paused,
        "mailbox": mailbox_target(),
        "label_analizados": analizados_label_name(),
        "gmail_connected": None,
        "current": current_msg,
    }


def list_messages(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    route: Optional[str] = None,
    classify: Optional[str] = None,
    cedula_filter: Optional[str] = None,
) -> Dict[str, Any]:
    from sqlalchemy import exists, or_, and_

    # Corrige Bandeja si el worker murió dejando filas en_proceso/en_cola.
    try:
        release_stale_in_flight_messages(db)
        normalize_active_lot_display(db)
    except Exception:
        logger.exception("[AUDITORIA_EMAIL] release_stale_in_flight falló")
        try:
            db.rollback()
        except Exception:
            pass

    stmt = select(AuditoriaEmailMessage)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (AuditoriaEmailMessage.subject.ilike(like))
            | (AuditoriaEmailMessage.from_email.ilike(like))
            | (AuditoriaEmailMessage.gmail_message_id.ilike(like))
        )
    if route:
        stmt = stmt.where(AuditoriaEmailMessage.route == route)
    if classify:
        stmt = stmt.where(AuditoriaEmailMessage.classify == classify)

    cf = (cedula_filter or "").strip()
    cf_low = cf.lower()
    # extract_json->>'cedula' (Postgres JSONB / JSON)
    try:
        ced_extract = AuditoriaEmailMessage.extract_json["cedula"].as_string()
    except Exception:
        ced_extract = None

    has_receipt_ced = exists(
        select(AuditoriaEmailReceipt.id).where(
            AuditoriaEmailReceipt.message_id == AuditoriaEmailMessage.id,
            AuditoriaEmailReceipt.cedula.isnot(None),
            func.length(func.trim(AuditoriaEmailReceipt.cedula)) > 0,
        )
    )

    if cf_low in ("na", "n/a", "sin", "sin_cedula", "sin-cedula"):
        # Sin cédula en extract ni en recibos
        if ced_extract is not None:
            empty_extract = or_(
                ced_extract.is_(None),
                func.trim(ced_extract) == "",
            )
            stmt = stmt.where(and_(empty_extract, ~has_receipt_ced))
        else:
            stmt = stmt.where(~has_receipt_ced)
    elif cf:
        like_c = f"%{cf}%"
        if ced_extract is not None:
            stmt = stmt.where(
                or_(
                    ced_extract.ilike(like_c),
                    exists(
                        select(AuditoriaEmailReceipt.id).where(
                            AuditoriaEmailReceipt.message_id
                            == AuditoriaEmailMessage.id,
                            AuditoriaEmailReceipt.cedula.ilike(like_c),
                        )
                    ),
                )
            )
        else:
            stmt = stmt.where(
                exists(
                    select(AuditoriaEmailReceipt.id).where(
                        AuditoriaEmailReceipt.message_id == AuditoriaEmailMessage.id,
                        AuditoriaEmailReceipt.cedula.ilike(like_c),
                    )
                )
            )

    total = int(
        db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0
    )
    rows = (
        db.execute(
            stmt.order_by(desc(AuditoriaEmailMessage.id)).offset(skip).limit(limit)
        )
        .scalars()
        .all()
    )
    items = [_message_dict(r) for r in rows]
    # Completar cédula desde recibos si el extract no la trae.
    missing = [it for it in items if not it.get("cedula") and it.get("id")]
    if missing:
        mids = [int(it["id"]) for it in missing]
        recs = (
            db.execute(
                select(AuditoriaEmailReceipt).where(
                    AuditoriaEmailReceipt.message_id.in_(mids),
                    AuditoriaEmailReceipt.cedula.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        by_msg: Dict[int, str] = {}
        for r in recs:
            if r.message_id and r.cedula and int(r.message_id) not in by_msg:
                by_msg[int(r.message_id)] = str(r.cedula).strip()
        for it in items:
            if not it.get("cedula") and it.get("id") in by_msg:
                it["cedula"] = by_msg[int(it["id"])]
                it["cedulaLabel"] = by_msg[int(it["id"])]
    for it in items:
        ced = str(it.get("cedula") or "").strip()
        it["cedula"] = ced or None
        it["cedulaLabel"] = ced if ced else "NA"
    return {
        "total": total,
        "items": items,
        "cedulaFilter": cf or None,
    }


def get_message(db: Session, message_id: int) -> Dict[str, Any]:
    msg = db.get(AuditoriaEmailMessage, message_id)
    if msg is None:
        raise ValueError("Mensaje no encontrado")
    recs = (
        db.execute(
            select(AuditoriaEmailReceipt).where(
                AuditoriaEmailReceipt.message_id == message_id
            )
        )
        .scalars()
        .all()
    )
    data = _message_dict(msg)
    data["recibos"] = [_receipt_dict(r) for r in recs]
    return data


def list_receipts(
    db: Session, *, skip: int = 0, limit: int = 50, status: Optional[str] = "pending"
) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import list_receipts as _list

    return _list(db, skip=skip, limit=limit, status=status)


def reset_cola_completa(db: Session) -> Dict[str, Any]:
    """
    Borra cola Auditoría Email para arrancar desde cero:
    - detiene todos los escaneos running
    - elimina recibos no aplicados a cuotas (pending/revision/…)
    - elimina todos los mensajes de Bandeja
    - elimina jobs de escaneo

    No toca ``pagos`` / cartera / Gmail. Conserva recibos ``approved`` con ``pago_id``.
    """
    # Cancelar workers en este proceso.
    running = (
        db.execute(
            select(AuditoriaEmailScan).where(AuditoriaEmailScan.status == "running")
        )
        .scalars()
        .all()
    )
    for scan in running:
        _request_cancel_scan(int(scan.id))
        _apply_user_stop(db, scan, page_token=scan.page_token)

    n_aprobados_conservados = int(
        db.execute(
            select(func.count())
            .select_from(AuditoriaEmailReceipt)
            .where(
                AuditoriaEmailReceipt.status == "approved",
                AuditoriaEmailReceipt.pago_id.isnot(None),
            )
        ).scalar_one()
        or 0
    )

    # Recibos sin alta a cuotas.
    del_rec = db.execute(
        delete(AuditoriaEmailReceipt).where(
            (AuditoriaEmailReceipt.pago_id.is_(None))
            | (AuditoriaEmailReceipt.status != "approved")
        )
    )
    n_recibos = int(del_rec.rowcount or 0)

    del_msg = db.execute(delete(AuditoriaEmailMessage))
    n_msgs = int(del_msg.rowcount or 0)

    del_scans = db.execute(delete(AuditoriaEmailScan))
    n_scans = int(del_scans.rowcount or 0)

    with _CANCEL_GUARD:
        _CANCEL_SCAN_IDS.clear()

    db.commit()
    logger.info(
        "[AUDITORIA_EMAIL] RESET cola: scans=%s msgs=%s recibos=%s conservados_approved=%s",
        n_scans,
        n_msgs,
        n_recibos,
        n_aprobados_conservados,
    )
    return {
        "ok": True,
        "scansEliminados": n_scans,
        "mensajesEliminados": n_msgs,
        "recibosEliminados": n_recibos,
        "recibosApprovedConservados": n_aprobados_conservados,
    }


def eliminar_mensajes_lote(db: Session, message_ids: List[int]) -> Dict[str, Any]:
    """
    Elimina mensajes de Bandeja + recibos pending ligados (y temporales).
    No borra recibos ya aplicados a cuotas (approved con pago_id).
    """
    from app.services.auditoria_email.receipts_service import eliminar_recibo

    ids = [int(x) for x in message_ids if x is not None]
    seen = set()
    ordered: List[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    if not ordered:
        raise ValueError("messageIds vacío")

    eliminados: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []
    omitidos: List[Dict[str, Any]] = []
    recibos_eliminados = 0

    for mid in ordered:
        try:
            msg = db.get(AuditoriaEmailMessage, mid)
            if msg is None:
                errores.append({"id": mid, "motivo": "no_encontrado"})
                continue

            recs = (
                db.execute(
                    select(AuditoriaEmailReceipt).where(
                        AuditoriaEmailReceipt.message_id == mid
                    )
                )
                .scalars()
                .all()
            )
            bloqueado = False
            for rec in recs:
                st = (rec.status or "").strip().lower() or "pending"
                if st == "approved" and rec.pago_id:
                    omitidos.append(
                        {
                            "id": mid,
                            "motivo": "tiene_recibo_aplicado",
                            "reciboId": int(rec.id),
                            "pagoId": int(rec.pago_id),
                        }
                    )
                    bloqueado = True
                    break
            if bloqueado:
                continue

            for rec in list(recs):
                st = (rec.status or "").strip().lower() or "pending"
                rid = int(rec.id)
                if st == "pending" or st == "revision":
                    eliminar_recibo(db, rid)
                    recibos_eliminados += 1
                else:
                    # approved sin pago_id u otros: borrar fila recibo
                    db.delete(rec)
                    db.flush()
                    recibos_eliminados += 1

            # Re-fetch message (eliminar_recibo hace commit)
            msg = db.get(AuditoriaEmailMessage, mid)
            if msg is not None:
                db.delete(msg)
                db.commit()
            eliminados.append({"id": mid, "ok": True})
        except ValueError as e:
            errores.append({"id": mid, "motivo": str(e)})
        except Exception as e:
            logger.exception("[AUDITORIA_EMAIL] eliminar bandeja id=%s: %s", mid, e)
            try:
                db.rollback()
            except Exception:
                pass
            errores.append({"id": mid, "motivo": "exception", "error": str(e)[:300]})

    return {
        "ok": True,
        "total": len(ordered),
        "eliminados": len(eliminados),
        "recibosEliminados": recibos_eliminados,
        "errores": len(errores),
        "omitidos": len(omitidos),
        "itemsEliminados": eliminados,
        "itemsErrores": errores,
        "itemsOmitidos": omitidos,
    }


def reescaneo(
    db: Session,
    *,
    message_ids: List[int],
    pipeline_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _ = pipeline_ids
    service, creds = _gmail_service()
    if service is None or creds is None:
        raise ValueError(
            f"Conecta {mailbox_target()} antes de re-escanear."
        )
    gmail_ids: List[str] = []
    rows: List[AuditoriaEmailMessage] = []
    msg_db_map: Dict[str, int] = {}
    for mid in message_ids:
        msg = db.get(AuditoriaEmailMessage, int(mid))
        if msg is None or not msg.gmail_message_id:
            continue
        rows.append(msg)
        gmail_ids.append(str(msg.gmail_message_id))
        msg_db_map[str(msg.gmail_message_id)] = int(msg.id)
    if not gmail_ids:
        return {"ok": True, "reescaneados": 0}
    sync_id, pipe_status = _run_pagos_pipeline_lot(db, message_ids=gmail_ids, creds=creds)
    anti = _post_pipeline_cola_recibos(
        db,
        pipe_status,
        sync_id=sync_id,
        candidate_message_ids=gmail_ids,
        message_db_by_gmail=msg_db_map,
    )
    listos = list((anti.get("analizados") or {}).get("listos") or [])
    omitidos = set(
        (anti.get("materializar") or {}).get("omitidos_no_aprobado") or []
    )
    outcomes = _sync_item_outcomes(db, sync_id, gmail_ids) if sync_id else {}
    targets: List[str] = []
    for msg in rows:
        mid = str(msg.gmail_message_id)
        oc = outcomes.get(mid) or {}
        dig = mid in set(listos) or int(oc.get("items") or 0) > 0
        targets.extend(
            _targets_analizados_adicional(
                gmail_message_id=mid,
                listos=listos,
                label_ids=list(msg.label_ids or []),
                digitalizado=dig,
                force_skip=mid in omitidos,
            )
        )
    labeled = _apply_analizados(service, targets) if targets else 0
    labeled_set = set(targets)
    for msg in rows:
        mid = str(msg.gmail_message_id)
        if mid in omitidos:
            msg.classify = "sin_prestamo_aprobado"
            msg.route = "omitido_no_aprobado"
            extract = dict(msg.extract_json or {})
            extract["omit_reason"] = "sin_prestamo_aprobado"
            msg.extract_json = extract
        else:
            cerrado = mid in set(listos)
            msg.classify = "digitalizado" if cerrado else "sin_digitalizacion"
            msg.route = "pendiente_aprobacion" if cerrado else "reintentar"
        aplicado = mid in labeled_set
        msg.pipelines_json = {
            "pipelines": [
                {
                    "id": "pagos_gmail.digitalizar",
                    "status": pipe_status,
                    "pagos_sync_id": sync_id,
                    "label": analizados_label_name() if aplicado else None,
                    "cola_recibos": anti,
                    "analizados_aplicado": aplicado,
                }
            ]
        }
        db.add(msg)
    db.commit()
    return {
        "ok": True,
        "reescaneados": len(gmail_ids),
        "pagos_sync_id": sync_id,
        "pipeline_status": pipe_status,
        "analizados_aplicados": labeled,
        "analizados_omitidos": len(gmail_ids) - labeled,
        "cola_recibos": anti,
        "omitidos_no_aprobado": list(omitidos),
    }


def alineamiento() -> Dict[str, Any]:
    st: Dict[str, Any] = {
        "ready_for_scan": False,
        "gmail_profile_email": None,
        "mailbox_target": mailbox_target(),
        "tokens_file_ready": cobranza_tokens_file_ready(),
    }
    try:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            st = connection_status(db)
        finally:
            db.close()
    except Exception as e:
        st["error"] = str(e)[:200]
        st["ready_for_scan"] = False
        # Sin BD aún se puede verificar archivo de tokens.
        st["ready_for_scan"] = False
        if cobranza_tokens_file_ready():
            st["tokens_file_ready"] = True

    q_sample = build_gmail_query({"newerThanDays": 7, "attachments": "pagos_gmail"})
    return {
        "manifest_version": MANIFEST_VERSION,
        "flujo": [
            "1. OAuth cobranza@ (tokens aparte)",
            "2. Filtro Gmail (criterios; incluye con/sin etiqueta; opcional -label:ANALIZADOS)",
            "3. Correo a correo → OCR/digitalizar (defer_autoconciliacion); Bandeja se actualiza al instante",
            "4. Materializar cola Recibos (pending) tras cada correo digitalizado",
            "5. Aprobar en Recibos → validadores + cuotas + cascada",
            "6. Revisión manual → pagos_con_errores",
            f"7. Etiqueta {analizados_label_name()} adicional (no reemplaza banco) "
            "si recibo / ya tenía etiqueta / digitalizó",
        ],
        "checks": [
            {
                "id": "conexion_cobranza",
                "ok": bool(st.get("ready_for_scan")),
                "detalle": (
                    f"Perfil {st.get('gmail_profile_email') or '—'} · "
                    f"objetivo {st.get('mailbox_target')} · "
                    f"tokens={'OK' if st.get('tokens_file_ready') else 'NO'} · "
                    f"path={st.get('tokens_path') or '—'}"
                    + (f" · err={st.get('error')}" if st.get("error") else "")
                ),
            },
            {
                "id": "filtro_gmail_incluye_etiquetados",
                "ok": f"-label:{analizados_label_name()}" not in q_sample,
                "detalle": (
                    f"Por defecto escanea con o sin etiqueta. Ejemplo q: {q_sample}"
                ),
            },
            {
                "id": "cola_recibos_aprobacion",
                "ok": True,
                "detalle": (
                    "Aprobar = validadores vigentes + cuotas/cascada; "
                    "si no pasa → pagos_con_errores y /pagos?pestana=revision."
                ),
            },
            {
                "id": "bandeja_minima",
                "ok": True,
                "detalle": "Bandeja: fecha correo + email + cédula/NA (filtros).",
            },
            {
                "id": "recibos_thumb_auth",
                "ok": True,
                "detalle": "Recibos usa ComprobanteThumb (JWT) para miniatura de comprobante.",
            },
            {
                "id": "lotes_100_async",
                "ok": True,
                "detalle": (
                    f"Lotes ≤{LOT_SIZE_MAX}; advance en background; UI/scheduler reanudan."
                ),
            },
            {
                "id": "anti_atasco_running",
                "ok": True,
                "detalle": (
                    f"running stale >{SCAN_STALE_RUNNING_MINUTES} min → paused reanudable."
                ),
            },
        ],
        "backlog": [
            "Cola dedicada si Pagos Gmail y Auditoría Email compiten por el advisory lock",
        ],
    }


def pipelines_catalog() -> List[Dict[str, Any]]:
    # El proceso real es Pagos Gmail; el catálogo heurístico queda como referencia UI.
    base = [
        {
            "id": "pagos_gmail.vigente",
            "nombre": "Pagos Gmail (OCR / cuotas / revisión)",
            "fase": "negocio",
        },
        {
            "id": "gmail.label_analizados",
            "nombre": f"Etiqueta {analizados_label_name()}",
            "fase": "cierre",
        },
    ]
    return base + list(PIPELINE_CATALOG)


def _message_dict(m: AuditoriaEmailMessage) -> Dict[str, Any]:
    extract = m.extract_json if isinstance(m.extract_json, dict) else {}
    cedula_raw = extract.get("cedula") if extract else None
    cedula = str(cedula_raw).strip() if cedula_raw else ""
    types = list(m.attachment_types or [])
    att_count = len(types) if types else (1 if m.has_attachment else 0)
    return {
        "id": m.id,
        "scanId": m.scan_id,
        "gmailMessageId": m.gmail_message_id,
        "gmailThreadId": m.gmail_thread_id,
        "source": m.source,
        "fromEmail": m.from_email,
        "fromName": m.from_name,
        "subject": m.subject,
        "snippet": m.snippet,
        "internalDate": m.internal_date.isoformat() if m.internal_date else None,
        "hasAttachment": m.has_attachment,
        "attachmentTypes": m.attachment_types,
        "attachmentCount": att_count,
        "attachmentMaxKb": m.attachment_max_kb,
        "cedula": cedula or None,
        "cedulaLabel": cedula if cedula else "NA",
        "classify": m.classify,
        "route": m.route,
        "slaHours": m.sla_hours,
        "riesgo": m.riesgo,
        "evidencia": m.evidencia,
        "extract": m.extract_json,
        "ocr": m.ocr_json,
        "pipelines": m.pipelines_json,
        "ingestedAt": m.ingested_at.isoformat() if m.ingested_at else None,
    }


def _receipt_dict(r: AuditoriaEmailReceipt) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import receipt_dict

    return receipt_dict(r)
