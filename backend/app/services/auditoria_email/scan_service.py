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
# running + Listados 0: el POST marcó running y nunca listó (timeout proxy,
# hang en credenciales, request cancelado). 90 s, no 10 min: el GET no es avance.
SCAN_LISTED_ZERO_STUCK_SECONDS = 90
# OCR del lote terminó pero un refresh dejó status=running: el scheduler
# no reanuda (solo mira paused). 2 min con candado libre = lote cerrado.
SCAN_LOTE_DONE_STUCK_SECONDS = 120
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
# Escaneos con hilo vivo en este worker. Lo consulta el keepalive de Gunicorn
# (backend/gunicorn.conf.py): sin latido el arbiter manda SIGABRT durante un
# lote largo de OCR y el hilo muere dejando el job «En curso» sin nadie detrás.
_SCANS_ACTIVOS: set[int] = set()
_SCANS_ACTIVOS_GUARD = threading.Lock()
# Perfil de cobranza@ cacheado: /status se pide cada 2 s desde la UI.
PERFIL_TTL_SEGUNDOS = 60
_PERFIL_CACHE: Dict[str, Any] = {
    "email": None,
    "connected": False,
    "error": None,
    "exp": 0.0,
}
_PERFIL_GUARD = threading.Lock()
# Conteos + origen OAuth: /status los pedía en cada poll y tardaba ~1 s
# (sync Informe pagos + COUNT de bandeja/recibos) mientras el escaneo lista.
_STATUS_EXTRA_TTL = 30.0
_STATUS_EXTRA_CACHE: Dict[str, Any] = {"exp": 0.0, "data": None}
_STATUS_EXTRA_GUARD = threading.Lock()
_STUCK_LIST_LOG_AT: Dict[int, float] = {}


def _marcar_scan_activo(scan_id: int, activo: bool) -> None:
    with _SCANS_ACTIVOS_GUARD:
        if activo:
            _SCANS_ACTIVOS.add(int(scan_id))
        else:
            _SCANS_ACTIVOS.discard(int(scan_id))


def hay_escaneos_email_activos() -> bool:
    """Contrato con el keepalive de Gunicorn. No debe lanzar nunca."""
    with _SCANS_ACTIVOS_GUARD:
        return bool(_SCANS_ACTIVOS)


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

    logger.info("[AUDITORIA_EMAIL] gmail client build start")
    creds = get_cobranza_gmail_credentials()
    if creds is None:
        logger.warning("[AUDITORIA_EMAIL] gmail client sin credenciales")
        return None, None
    service = build_gmail_service(creds)
    logger.info("[AUDITORIA_EMAIL] gmail client build ok")
    return service, creds


def _perfil_gmail_cobranza() -> Tuple[Optional[str], bool, Optional[str]]:
    """(email, conectado, error) con caché corta.

    La UI pide /status cada 2 s y cada llamada hacía un getProfile a Gmail:
    ~1 s de latencia por request y cuota quemada mientras el escaneo lista
    mensajes. El TTL corto basta para que una reconexión se note enseguida.
    """
    ahora = time.time()
    with _PERFIL_GUARD:
        if _PERFIL_CACHE["exp"] > ahora:
            return (
                _PERFIL_CACHE["email"],
                bool(_PERFIL_CACHE["connected"]),
                _PERFIL_CACHE["error"],
            )
    service, _ = _gmail_service()
    email: Optional[str] = None
    connected = False
    err: Optional[str] = None
    if service is not None:
        try:
            prof = service.users().getProfile(userId="me").execute()
            email = (prof.get("emailAddress") or "").strip() or None
            connected = True
        except Exception as e:
            err = str(e)[:400]
            logger.warning("[AUDITORIA_EMAIL] perfil Gmail: %s", e)
    with _PERFIL_GUARD:
        _PERFIL_CACHE.update(
            {
                "email": email,
                "connected": connected,
                "error": err,
                # Un fallo no se cachea tanto: puede ser un corte pasajero.
                "exp": ahora + (PERFIL_TTL_SEGUNDOS if connected else 10),
            }
        )
    return email, connected, err


def invalidar_perfil_gmail_cache() -> None:
    with _PERFIL_GUARD:
        _PERFIL_CACHE["exp"] = 0.0


def connection_status(db: Session) -> Dict[str, Any]:
    profile_email, connected, err = _perfil_gmail_cobranza()
    mode = "gmail" if connected else "disconnected"
    target = mailbox_target()
    mailbox_match: Optional[bool] = None
    if connected and profile_email and target:
        mailbox_match = profile_email.lower() == target.lower()
    ready = bool(connected and mailbox_match is not False)
    ahora = time.time()
    extra: Optional[Dict[str, Any]] = None
    with _STATUS_EXTRA_GUARD:
        if _STATUS_EXTRA_CACHE["exp"] > ahora and isinstance(
            _STATUS_EXTRA_CACHE.get("data"), dict
        ):
            extra = dict(_STATUS_EXTRA_CACHE["data"])
    if extra is None:
        n_msg = int(
            db.execute(select(func.count()).select_from(AuditoriaEmailMessage)).scalar_one()
            or 0
        )
        n_rec = int(
            db.execute(select(func.count()).select_from(AuditoriaEmailReceipt)).scalar_one()
            or 0
        )
        _, tokens_storage = load_cobranza_gmail_token_payload()
        extra = {
            "tokens_path": _cobranza_tokens_path(),
            "tokens_file_ready": cobranza_tokens_file_ready(),
            "tokens_storage": tokens_storage,
            "label_analizados": analizados_label_name(),
            "mensajes_bd": n_msg,
            "recibos_bd": n_rec,
            "manifest_version": MANIFEST_VERSION,
            "oauth_redirect_hint": (
                f"...{getattr(settings, 'API_V1_STR', '/api/v1')}/auditoria/email/oauth/callback"
            ),
            **cobranza_oauth_config_status(),
        }
        with _STATUS_EXTRA_GUARD:
            _STATUS_EXTRA_CACHE["exp"] = ahora + _STATUS_EXTRA_TTL
            _STATUS_EXTRA_CACHE["data"] = dict(extra)
    return {
        "mailbox_target": target,
        "gmail_connected": connected,
        "gmail_profile_email": profile_email,
        "mailbox_match": mailbox_match,
        "ready_for_scan": ready and connected,
        "source_mode": mode,
        "error": err,
        **extra,
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
    filename = (part.get("filename") or "").strip()
    body = part.get("body") or {}
    size = int(body.get("size") or 0)
    mime = (part.get("mimeType") or "").strip().lower()
    if filename:
        files.append((str(filename), size))
    elif (
        mime.startswith("image/")
        or mime == "application/pdf"
        or "wordprocessingml" in mime
        or mime == "application/msword"
    ):
        # Foto pegada: Gmail a menudo no pone filename. Contarla igual.
        ext = mime.split("/", 1)[-1].split("+", 1)[0] or "bin"
        if ext == "jpeg":
            ext = "jpg"
        elif "wordprocessingml" in mime:
            ext = "docx"
        elif mime == "application/msword":
            ext = "doc"
        files.append((f"inline_body.{ext}", size))
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
        # Con warning y sin traza esto era invisible: el correo quedaba
        # «digitalizado» en Bandeja y Recibos vacío, sin nada que explicara
        # por qué. El fallo no aborta el lote, pero tiene que dejar rastro.
        logger.exception(
            "[AUDITORIA_EMAIL] materializar recibos falló sync=%s mensajes=%s: %s",
            sync_id,
            list(candidate_message_ids or [])[:5],
            e,
        )
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
        force_finish_gmail_pipeline_sync,
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
    try:
        sync_id, status = run_pipeline(
            db,
            existing_sync_id=sync.id,
            only_message_ids=list(message_ids),
            gmail_credentials=creds,
            defer_autoconciliacion=True,
            solo_clientes_aprobados=True,
        )
        return sync_id, status
    except Exception as e:
        # Si el worker muere a mitad, el finally de este hilo no corre; el
        # stale heal sigue siendo la red. Si *sí* llega una excepción, no
        # dejar la fila running 20 min–2 h bloqueando el siguiente lote.
        force_finish_gmail_pipeline_sync(
            db,
            getattr(sync, "id", None),
            status="error",
            error_message=str(e)[:500],
        )
        raise


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


def _advance_gmail(
    db: Session,
    scan: AuditoriaEmailScan,
    max_lots: int,
    *,
    defer_ocr: bool = False,
    accepted_override: Optional[List[Dict[str, Any]]] = None,
    next_token_override: Optional[str] = None,
) -> Dict[str, Any]:
    logger.info(
        "[AUDITORIA_EMAIL] advance pre-gmail scan=%s lots=%s defer_ocr=%s",
        scan.id,
        max_lots,
        defer_ocr,
    )
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
        if accepted_override:
            accepted_rows = list(accepted_override)
            next_token = next_token_override
            refs = accepted_rows
            accepted_override = None
            logger.info(
                "[AUDITORIA_EMAIL] OCR lote ya listado scan=%s n=%s",
                scan.id,
                len(accepted_rows),
            )
            # Caemos al bloque `if accepted_rows` más abajo (sin volver a listar).
            listed = len(accepted_rows)
            rejected = 0
            use_ocr_override = True
        else:
            use_ocr_override = False
        remaining = int(scan.max_messages) - int(scan.processed_total or 0)
        page_size = min(LOT_SIZE_MAX, int(scan.lot_size or LOT_SIZE_MAX), remaining)
        if page_size <= 0:
            break
        if not use_ocr_override:
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
            # Contador visible YA, antes de bajar cada mensaje. Si no, Listados
            # quedaba 0 todo el rato que tardaba el primer get() y la UI mentía.
            scan.listed_total = int(scan.listed_total or 0) + len(refs)
            scan.updated_at = _utcnow()
            if scan.status != "paused":
                scan.status = "running"
            db.add(scan)
            db.commit()
            logger.info(
                "[AUDITORIA_EMAIL] listed visible scan=%s +%s total=%s",
                scan.id,
                len(refs),
                scan.listed_total,
            )
            _heartbeat_scan(db, scan, note="post_list")
            accepted_rows = []
            listed = 0
            rejected = 0
            rejected_flushed = 0

            for ref in refs:
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                mid = ref.get("id")
                if not mid:
                    continue
                listed += 1
                if listed % 25 == 0:
                    logger.info(
                        "[AUDITORIA_EMAIL] fetch progreso scan=%s listed=%s aceptados=%s",
                        scan.id,
                        listed,
                        len(accepted_rows),
                    )
                if listed % 5 == 0:
                    scan.rejected_total = int(scan.rejected_total or 0) + (
                        rejected - rejected_flushed
                    )
                    rejected_flushed = rejected
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

            scan.rejected_total = int(scan.rejected_total or 0) + (
                rejected - rejected_flushed
            )
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
            if defer_ocr:
                # El POST /scans lista aquí (mismo hilo HTTP que el estimate,
                # que sí funciona). El OCR va en un hilo aparte: si el hilo
                # no arranca, Listados y Bandeja ya no quedan en 0.
                # Guardar el cursor YA: si el hilo OCR muere o un refresh
                # pisa paused, el lote 2 no se pierde.
                scan.page_token = next_token
                scan.status = "running"
                scan.updated_at = _utcnow()
                db.add(scan)
                db.commit()
                logger.info(
                    "[AUDITORIA_EMAIL] lote listo para OCR scan=%s accepted=%s next_page=%s",
                    scan.id,
                    len(accepted_rows),
                    bool(next_token),
                )
                out = _scan_dict(scan)
                out["_accepted_rows"] = accepted_rows
                out["_next_token"] = next_token
                out["_had_refs"] = True
                return out

            # 2) Un lock / una fila PagosGmailSync para TODO el lote.
            # Llamar al pipeline correo a correo reservaba el candado N veces y,
            # si el worker moría, Auditoría quedaba bloqueada 20 min–2 h.
            lote_ids = [str(r["gmail_message_id"]) for r in accepted_rows]
            for raw in accepted_rows:
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
            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=page_token)
            scan.updated_at = _utcnow()
            if scan.status != "paused":
                scan.status = "running"
            db.add(scan)
            db.commit()
            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=page_token)
            try:
                sync_id, pipe_status = _run_pagos_pipeline_lot(
                    db, message_ids=lote_ids, creds=creds
                )
            except Exception as e:
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                scan.last_error = str(e)[:1000]
                scan.status = "paused"
                scan.page_token = page_token
                scan.updated_at = _utcnow()
                for raw in accepted_rows:
                    if _pipeline_busy_error(e):
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
                _release_in_flight_for_scan(db, int(scan.id))
                db.add(scan)
                db.commit()
                raise

            if _stop_requested(db, int(scan.id)):
                return _apply_user_stop(db, scan, page_token=page_token)
            outcomes = _sync_item_outcomes(db, sync_id, lote_ids)
            mig = _post_pipeline_cola_recibos(
                db,
                pipe_status,
                sync_id=sync_id,
                candidate_message_ids=lote_ids,
                message_db_by_gmail=msg_db_map,
            )
            listos = list((mig.get("analizados") or {}).get("listos") or [])
            for raw in accepted_rows:
                if _stop_requested(db, int(scan.id)):
                    return _apply_user_stop(db, scan, page_token=page_token)
                mid = str(raw["gmail_message_id"])
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
                digitalizado = bool(oc and int(oc.get("items") or 0) > 0) or mid in set(listos)
                digitalizado_for_label = digitalizado
                listos_for_label = [mid] if mid in listos else []
                targets = _targets_analizados_adicional(
                    gmail_message_id=mid,
                    listos=listos_for_label,
                    label_ids=list(raw.get("label_ids") or []),
                    digitalizado=digitalizado_for_label,
                    force_skip=False,
                )
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
            if _cancel_requested(int(scan.id)) or _user_stopped_scan(scan):
                return _apply_user_stop(
                    db, scan, page_token=None if hit_cap or no_more else page_token
                )
            # Commit YA. _stop_requested hace db.refresh() y si complete
            # no está persistido, SQLAlchemy lo pisa con el último
            # «running» (lote filtrado) y el job queda En curso eterno
            # con Listados 0 — #15/#16 con inbox vacío.
            scan.page_token = None
            scan.status = "complete"
            scan.finished_at = _utcnow()
            scan.last_error = None
            scan.updated_at = _utcnow()
            db.add(scan)
            db.commit()
            logger.info(
                "[AUDITORIA_EMAIL] complete scan=%s listed=%s processed=%s "
                "refs=%s next_page=%s",
                scan.id,
                scan.listed_total,
                scan.processed_total,
                len(refs or []),
                bool(next_token),
            )
            return _scan_dict(scan)
        if _cancel_requested(int(scan.id)) or _user_stopped_scan(scan):
            return _apply_user_stop(db, scan, page_token=next_token)
        # Commit paused+cursor YA. El mismo refresh de _stop_requested
        # que dejaba complete→running deja el lote 2 sin arrancar
        # (OCR fin status=running, scheduler «sin jobs reanudables»).
        scan.page_token = next_token
        scan.status = "paused"
        if not _user_stopped_scan(scan):
            scan.last_error = None
        scan.updated_at = _utcnow()
        db.add(scan)
        db.commit()
        logger.info(
            "[AUDITORIA_EMAIL] lote pausado scan=%s processed=%s next_page=%s",
            scan.id,
            scan.processed_total,
            bool(next_token),
        )
        return _scan_dict(scan)

    if scan.status in ("complete", "paused"):
        return _scan_dict(scan)
    if _stop_requested(db, int(scan.id)) or _user_stopped_scan(scan):
        return _apply_user_stop(db, scan, page_token=scan.page_token)
    scan.updated_at = _utcnow()
    db.add(scan)
    db.commit()
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


def _scan_looks_listed_zero_stuck(scan: AuditoriaEmailScan) -> bool:
    """running con Listados 0: no hay listado Gmail, da igual el candado."""
    if scan.status != "running":
        return False
    if int(scan.listed_total or 0) > 0 or int(scan.processed_total or 0) > 0:
        return False
    ts = scan.updated_at or scan.created_at
    if not ts:
        return True
    return (_utcnow() - ts).total_seconds() >= SCAN_LISTED_ZERO_STUCK_SECONDS


def _scan_looks_lote_ocr_terminado_sin_pausa(scan: AuditoriaEmailScan) -> bool:
    """Lote digitalizado, hilo muerto, job quedó running → no hay lote 2."""
    if scan.status != "running":
        return False
    if _advance_lock_for(int(scan.id)).locked():
        return False
    if int(scan.processed_total or 0) <= 0:
        return False
    ts = scan.updated_at or scan.created_at
    if not ts:
        return True
    return (_utcnow() - ts).total_seconds() >= SCAN_LOTE_DONE_STUCK_SECONDS


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
    # Al reanudar arranca una corrida nueva: cualquier aviso previo (Detener,
    # «sin latido», «pipeline ocupado») queda obsoleto. Si no se limpiaba, la
    # UI seguía mostrando el job como muerto aunque estuviera avanzando.
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


def _ocr_gmail_background(
    scan_id: int,
    accepted_rows: List[Dict[str, Any]],
    next_token: Optional[str],
    lock: threading.Lock,
) -> None:
    logger.info(
        "[AUDITORIA_EMAIL] hilo OCR despachado scan=%s n=%s",
        scan_id,
        len(accepted_rows),
    )
    from app.core.database import SessionLocal

    db = SessionLocal()
    _marcar_scan_activo(scan_id, True)
    try:
        scan = db.get(AuditoriaEmailScan, scan_id)
        if scan is None:
            logger.warning("[AUDITORIA_EMAIL] hilo OCR sin scan=%s", scan_id)
            return
        logger.info("[AUDITORIA_EMAIL] hilo OCR inicio scan=%s n=%s", scan_id, len(accepted_rows))
        out = _advance_gmail(
            db,
            scan,
            1,
            accepted_override=list(accepted_rows),
            next_token_override=next_token,
        )
        logger.info(
            "[AUDITORIA_EMAIL] hilo OCR fin scan=%s status=%s procesados=%s",
            scan_id,
            out.get("status"),
            out.get("processedTotal"),
        )
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] hilo OCR scan=%s: %s", scan_id, e)
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
        _marcar_scan_activo(scan_id, False)
        db.close()
        lock.release()


def _advance_gmail_background(
    scan_id: int,
    max_lots: int,
    lock: Optional[threading.Lock] = None,
) -> None:
    logger.info("[AUDITORIA_EMAIL] hilo listado despachado scan=%s", scan_id)
    from app.core.database import SessionLocal

    # El candado lo toma advance_scan antes de marcar running y cede la
    # propiedad a este hilo. Si el hilo lo tomara aquí y fallara, el escaneo
    # quedaría running en BD sin nadie trabajando (fantasma de ~10 min hasta
    # el heal de huérfano).
    if lock is None:
        lock = _advance_lock_for(scan_id)
        if not lock.acquire(blocking=False):
            logger.info(
                "[AUDITORIA_EMAIL] advance ya en curso (skip hilo) scan=%s", scan_id
            )
            return
    db = SessionLocal()
    _marcar_scan_activo(scan_id, True)
    try:
        scan = db.get(AuditoriaEmailScan, scan_id)
        if scan is None:
            logger.warning("[AUDITORIA_EMAIL] hilo sin scan=%s en BD", scan_id)
            return
        logger.info("[AUDITORIA_EMAIL] hilo inicio scan=%s lots=%s", scan_id, max_lots)
        out = _advance_gmail(db, scan, max_lots)
        logger.info(
            "[AUDITORIA_EMAIL] hilo fin scan=%s status=%s procesados=%s listados=%s",
            scan_id,
            out.get("status"),
            out.get("processedTotal"),
            out.get("listedTotal"),
        )
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
        _marcar_scan_activo(scan_id, False)
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
        logger.info(
            "[AUDITORIA_EMAIL] advance skip alreadyRunning (candado local) scan=%s",
            scan_id,
        )
        out = _scan_dict(scan)
        out["alreadyRunning"] = True
        return out

    listed_zero = _scan_looks_listed_zero_stuck(scan)
    lote_done = _scan_looks_lote_ocr_terminado_sin_pausa(scan)
    if scan.status == "running" and (
        _scan_looks_stale_running(scan)
        or _scan_looks_orphaned_running(scan, db)
        or listed_zero
        or lote_done
    ):
        scan.status = "paused"
        scan.last_error = (
            scan.last_error
            or (
                "Reanudable: listado Gmail no arrancó (Listados 0)"
                if listed_zero
                else (
                    "Reanudable: lote OCR terminado; sigue la página siguiente"
                    if lote_done
                    else (
                        f"Reanudable: corrida previa sin latido >{SCAN_STALE_RUNNING_MINUTES} min"
                        if _scan_looks_stale_running(scan)
                        else f"Reanudable: worker OCR sin latido >{SCAN_ORPHAN_RUNNING_MINUTES} min"
                    )
                )
            )
        )
        _release_in_flight_for_scan(db, int(scan.id))
        db.add(scan)
        db.commit()
        db.refresh(scan)
    elif scan.status == "running":
        if int(scan.listed_total or 0) == 0 and int(scan.processed_total or 0) == 0:
            # Fantasma: running sin listar. Reanudar debe volver a listar,
            # no devolver alreadyRunning (eso dejó #15/#16 en 0 eterno).
            logger.warning(
                "[AUDITORIA_EMAIL] advance relista scan=%s running listed=0",
                scan_id,
            )
            scan.status = "paused"
            scan.last_error = "Reanudable: listado Gmail no arrancó (Listados 0)"
            _release_in_flight_for_scan(db, int(scan.id))
            db.add(scan)
            db.commit()
            db.refresh(scan)
        elif int(scan.processed_total or 0) > 0 and not lock.locked():
            # #19: OCR fin dejó running; Reanudar no debe decir alreadyRunning.
            logger.warning(
                "[AUDITORIA_EMAIL] advance sigue lote scan=%s running processed=%s "
                "sin candado",
                scan_id,
                scan.processed_total,
            )
            scan.status = "paused"
            if not (scan.last_error or "").startswith("Detenido"):
                scan.last_error = (
                    "Reanudable: lote OCR terminado; sigue la página siguiente"
                )
            _release_in_flight_for_scan(db, int(scan.id))
            db.add(scan)
            db.commit()
            db.refresh(scan)
        else:
            logger.info(
                "[AUDITORIA_EMAIL] advance skip alreadyRunning (BD running, no huérfano) "
                "scan=%s updated_at=%s",
                scan_id,
                scan.updated_at,
            )
            out = _scan_dict(scan)
            out["alreadyRunning"] = True
            return out

    assert_ready_for_scan(db)
    max_lots = max(1, min(int(max_lots or 1), 3))

    # Tomar el candado ANTES de marcar running: si otro hilo lo tiene (p. ej. el
    # anterior aún cerrando su sesión), salimos sin tocar la BD. Al revés el
    # escaneo quedaba running sin worker y la UI mostraba «En curso» inmóvil.
    if not lock.acquire(blocking=False):
        logger.info(
            "[AUDITORIA_EMAIL] advance skip alreadyRunning (no tomó candado) scan=%s",
            scan_id,
        )
        out = _scan_dict(scan)
        out["alreadyRunning"] = True
        return out

    liberar = True
    try:
        _clear_cancel_scan(scan_id)
        _clear_user_stop_flag(scan)
        # No marcar running aquí: si el listado Gmail no arranca, la UI
        # mostraba «En curso» con Listados 0 y Reanudar se negaba (alreadyRunning).
        scan.updated_at = _utcnow()
        db.add(scan)
        db.commit()
        db.refresh(scan)
        logger.info(
            "[AUDITORIA_EMAIL] advance HTTP list scan=%s status=%s",
            scan_id,
            scan.status,
        )

        if not background:
            _marcar_scan_activo(scan_id, True)
            try:
                return _advance_gmail(db, scan, max_lots)
            finally:
                _marcar_scan_activo(scan_id, False)

        # Listar Gmail EN ESTE hilo (el mismo que estimate, que sí responde).
        # El hilo daemon solo hace OCR. Si el daemon no arranca, Listados y
        # Bandeja ya tienen datos: el job no queda en 0/32000 eterno.
        # Keepalive de Gunicorn: el list/fetch bloquea el event loop; sin
        # sonda activa el arbiter puede SIGABRT al worker a los ~30 s.
        _marcar_scan_activo(scan_id, True)
        primed = _advance_gmail(db, scan, 1, defer_ocr=True)
        accepted = list(primed.pop("_accepted_rows", None) or [])
        next_tok = primed.pop("_next_token", None)
        primed.pop("_had_refs", None)
        db.refresh(scan)
        if accepted:
            threading.Thread(
                target=_ocr_gmail_background,
                args=(scan_id, accepted, next_tok, lock),
                name=f"auditoria-email-ocr-{scan_id}",
                daemon=True,
            ).start()
            liberar = False
        else:
            _marcar_scan_activo(scan_id, False)
        return _scan_dict(scan)
    except Exception:
        # Ni hilo ni lote: devolver el escaneo a paused para que sea reanudable
        # ya mismo, sin esperar los 10 min del heal de huérfano.
        _marcar_scan_activo(scan_id, False)
        try:
            scan.status = "paused"
            scan.updated_at = _utcnow()
            db.add(scan)
            db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        if liberar:
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
    listed_zero = _scan_looks_listed_zero_stuck(scan)
    lote_done = _scan_looks_lote_ocr_terminado_sin_pausa(scan)
    if (
        _scan_looks_orphaned_running(scan, db)
        or _scan_looks_stale_running(scan)
        or listed_zero
        or lote_done
    ):
        scan.status = "paused"
        scan.last_error = (
            scan.last_error
            or (
                "Reanudable: listado Gmail no arrancó (Listados 0)"
                if listed_zero
                else (
                    "Reanudable: lote OCR terminado; sigue la página siguiente"
                    if lote_done
                    else f"Reanudable: worker OCR sin latido >{SCAN_ORPHAN_RUNNING_MINUTES} min"
                )
            )
        )
        scan.updated_at = _utcnow()
        _release_in_flight_for_scan(db, int(scan_id))
        db.add(scan)
        db.commit()
        db.refresh(scan)
        logger.info("[AUDITORIA_EMAIL] heal orphan scan=%s → paused", scan_id)
    return _scan_dict(scan)


def _collect_auto_advance_candidates(
    db: Session, max_scans: int
) -> List[AuditoriaEmailScan]:
    """
    Candidatos a reanudar, excluyendo los detenidos por el usuario.

    Sobrecarga el fetch para que un job ``Detenido`` no ocupe el cupo y
    tape a otros pausados reanudables.
    """
    max_scans = max(1, min(int(max_scans or 1), 3))
    fetch_n = max(max_scans * 8, 12)
    out: List[AuditoriaEmailScan] = []
    vistos: set[int] = set()

    def _take(scan: AuditoriaEmailScan) -> bool:
        sid = int(scan.id)
        if sid in vistos:
            return False
        if _user_stopped_scan(scan):
            return False
        vistos.add(sid)
        out.append(scan)
        return len(out) >= max_scans

    # Prioridad: con cursor (mitad de camino).
    for s in (
        db.execute(
            select(AuditoriaEmailScan)
            .where(
                AuditoriaEmailScan.status == "paused",
                AuditoriaEmailScan.page_token.isnot(None),
            )
            .order_by(AuditoriaEmailScan.id.asc())
            .limit(fetch_n)
        )
        .scalars()
        .all()
    ):
        if _take(s):
            return out

    # Pausados sin cursor que aún no terminaron.
    for s in (
        db.execute(
            select(AuditoriaEmailScan)
            .where(
                AuditoriaEmailScan.status == "paused",
                AuditoriaEmailScan.page_token.is_(None),
                AuditoriaEmailScan.finished_at.is_(None),
            )
            .order_by(desc(AuditoriaEmailScan.id))
            .limit(fetch_n)
        )
        .scalars()
        .all()
    ):
        if int(s.processed_total or 0) >= int(s.max_messages or 0):
            continue
        if _take(s):
            return out

    # Running huérfano / stale (mismo criterio que advance_scan).
    for s in (
        db.execute(
            select(AuditoriaEmailScan)
            .where(AuditoriaEmailScan.status == "running")
            .order_by(AuditoriaEmailScan.id.asc())
            .limit(fetch_n)
        )
        .scalars()
        .all()
    ):
        if _user_stopped_scan(s):
            continue
        if not (
            _scan_looks_stale_running(s)
            or _scan_looks_orphaned_running(s, db)
            or _scan_looks_listed_zero_stuck(s)
            or _scan_looks_lote_ocr_terminado_sin_pausa(s)
        ):
            continue
        logger.info(
            "[AUDITORIA_EMAIL] auto-avance rescata scan=%s running sin latido",
            s.id,
        )
        if _take(s):
            return out

    return out


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

    Los detenidos por el usuario no se reanudan ni disparan build de Gmail.
    """
    lots = max_lots
    if lots is None:
        lots = int(getattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_MAX_LOTS", 2) or 2)
    lots = max(1, min(int(lots), 3))
    max_scans = max(1, min(int(max_scans or 1), 3))

    # Primero candidatos (sin Gmail): si solo hay Detenidos, no quemar OAuth.
    rows = _collect_auto_advance_candidates(db, max_scans)
    if not rows:
        logger.info("[AUDITORIA_EMAIL] auto-avance sin jobs reanudables")
        return {"ok": True, "advanced": [], "max_lots": lots}

    try:
        assert_ready_for_scan(db)
    except ValueError as e:
        return {"ok": False, "reason": str(e)[:300], "advanced": []}

    advanced: List[Dict[str, Any]] = []
    for scan in rows:
        if _user_stopped_scan(scan):
            # Carrera: lo detuvieron entre el listado y el advance.
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
        # «paused» significa reanudable, y de ello depende el auto-reanudar de la
        # UI. Antes exigía pageToken o cero progreso, así que un lote que falló a
        # media faena (progreso > 0, cursor aún sin fijar) salía como NO
        # reanudable y el escaneo solo avanzaba al ritmo del scheduler.
        "paused": (
            scan.status == "paused"
            and scan.finished_at is None
            and int(scan.processed_total or 0) < int(scan.max_messages or 0)
        ),
        "stopped": _user_stopped_scan(scan),
        "labelAnalizados": analizados_label_name(),
    }


def get_scan(db: Session, scan_id: int) -> Dict[str, Any]:
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if scan.status == "running" and (
        _scan_looks_orphaned_running(scan, db)
        or _scan_looks_stale_running(scan)
        or _scan_looks_listed_zero_stuck(scan)
        or _scan_looks_lote_ocr_terminado_sin_pausa(scan)
    ):
        return heal_orphaned_scan(db, scan_id)
    if (
        scan.status == "running"
        and int(scan.listed_total or 0) == 0
        and int(scan.processed_total or 0) == 0
    ):
        now = time.time()
        last = _STUCK_LIST_LOG_AT.get(int(scan.id), 0.0)
        if now - last >= 30:
            _STUCK_LIST_LOG_AT[int(scan.id)] = now
            logger.warning(
                "[AUDITORIA_EMAIL] scan=%s running con listed=0 processed=0 "
                "updated_at=%s. El GET no es avance: no hay listado Gmail.",
                scan.id,
                scan.updated_at,
            )
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
    from app.services.prestamos.cedula_aprobada import attach_prestamo_estado_items

    attach_prestamo_estado_items(db, items)
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
    from app.services.prestamos.cedula_aprobada import attach_prestamo_estado_items

    attach_prestamo_estado_items(db, [data])
    attach_prestamo_estado_items(db, data["recibos"])
    return data


def list_receipts(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = "pending",
    prestamo_estado: Optional[str] = None,
) -> Dict[str, Any]:
    from app.services.auditoria_email.receipts_service import list_receipts as _list

    return _list(
        db,
        skip=skip,
        limit=limit,
        status=status,
        prestamo_estado=prestamo_estado,
    )


def _clear_runtime_scan_state() -> None:
    """Limpia señales/candados en memoria del worker (tras reset o wipe)."""
    with _CANCEL_GUARD:
        _CANCEL_SCAN_IDS.clear()
    with _SCANS_ACTIVOS_GUARD:
        _SCANS_ACTIVOS.clear()
    with _ADVANCE_LOCKS_GUARD:
        _ADVANCE_LOCKS.clear()
    _STUCK_LIST_LOG_AT.clear()


def reset_cola_completa(db: Session) -> Dict[str, Any]:
    """
    Borra cola Auditoría Email para arrancar desde cero:
    - fuerza detención de **todos** los jobs (running / paused / detenidos)
    - libera in-flight y candados en memoria
    - elimina recibos no aplicados a cuotas (pending/revision/…)
    - elimina temporales Gmail ligados a esos recibos
    - elimina todos los mensajes de Bandeja
    - elimina jobs de escaneo (incluida la «última acción» detenida)

    No toca ``pagos`` / cartera / Gmail inbox. Conserva recibos ``approved`` con ``pago_id``.
    """
    from app.models.pagos_gmail_sync import GmailTemporal

    todos = (
        db.execute(select(AuditoriaEmailScan).order_by(AuditoriaEmailScan.id.asc()))
        .scalars()
        .all()
    )
    n_forzados = 0
    for scan in todos:
        sid = int(scan.id)
        _request_cancel_scan(sid)
        _marcar_scan_activo(sid, False)
        # Aunque ya esté paused/Detenido: señal + liberar cola para el wipe.
        if (scan.status or "").strip().lower() != "complete":
            n_forzados += 1
        try:
            _release_in_flight_for_scan(db, sid)
        except Exception:
            logger.exception(
                "[AUDITORIA_EMAIL] RESET: release in-flight scan=%s", sid
            )

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

    # Temporales de recibos que vamos a borrar (no los approved con pago).
    a_borrar = (
        db.execute(
            select(AuditoriaEmailReceipt).where(
                (AuditoriaEmailReceipt.pago_id.is_(None))
                | (AuditoriaEmailReceipt.status != "approved")
            )
        )
        .scalars()
        .all()
    )
    temporal_ids: set[int] = set()
    temporal_mids: set[str] = set()
    for rec in a_borrar:
        if rec.gmail_temporal_id:
            try:
                temporal_ids.add(int(rec.gmail_temporal_id))
            except (TypeError, ValueError):
                pass
        mid = (rec.gmail_message_id or "").strip()
        if mid:
            temporal_mids.add(mid)

    n_temporales = 0
    if temporal_ids or temporal_mids:
        try:
            with db.begin_nested():
                if temporal_ids:
                    r1 = db.execute(
                        delete(GmailTemporal).where(
                            GmailTemporal.id.in_(list(temporal_ids))
                        )
                    )
                    n_temporales += int(r1.rowcount or 0)
                if temporal_mids:
                    r2 = db.execute(
                        delete(GmailTemporal).where(
                            GmailTemporal.gmail_message_id.in_(list(temporal_mids))
                        )
                    )
                    n_temporales += int(r2.rowcount or 0)
        except Exception:
            logger.exception(
                "[AUDITORIA_EMAIL] RESET: limpieza GmailTemporal falló (sigo wipe)"
            )

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

    _clear_runtime_scan_state()
    db.commit()
    logger.info(
        "[AUDITORIA_EMAIL] RESET cola: scans=%s forzados=%s msgs=%s recibos=%s "
        "temporales≈%s conservados_approved=%s",
        n_scans,
        n_forzados,
        n_msgs,
        n_recibos,
        n_temporales,
        n_aprobados_conservados,
    )
    return {
        "ok": True,
        "scansEliminados": n_scans,
        "scansDetenidos": n_forzados,
        "mensajesEliminados": n_msgs,
        "recibosEliminados": n_recibos,
        "temporalesEliminados": n_temporales,
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
                force_skip=False,
            )
        )
    labeled = _apply_analizados(service, targets) if targets else 0
    labeled_set = set(targets)
    for msg in rows:
        mid = str(msg.gmail_message_id)
        cerrado = mid in set(listos) or int(
            (outcomes.get(mid) or {}).get("items") or 0
        ) > 0
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
        "omitidos_no_aprobado": list(
            (anti.get("materializar") or {}).get("omitidos_no_aprobado") or []
        ),
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
