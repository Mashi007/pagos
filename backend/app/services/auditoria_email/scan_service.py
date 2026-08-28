"""
Servicio de escaneo Auditoría Email (buzón cobranza@).

Flujo: filtro Gmail (incluye ``-label:ANALIZADOS``) → lotes ≤100 → pipeline Pagos Gmail
vigente (OCR/Gemini/cuotas/revisión) → anti-limbo acotado → etiqueta ANALIZADOS solo si el
mensaje ya no está en limbo (``gmail_temporal``).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from email.utils import parseaddr
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
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

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "2.4.0"
LOT_SIZE_MAX = 100
# Escaneo stuck en running (HTTP cortado / worker caído) → se puede reanudar.
SCAN_STALE_RUNNING_MINUTES = 15


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
    cid = (
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_ID", None)
        or getattr(settings, "GOOGLE_CLIENT_ID", None)
    )
    csec = (
        getattr(settings, "AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET", None)
        or getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    )
    if not cid or not csec:
        try:
            from app.core.informe_pagos_config_holder import (
                get_google_oauth_client_id,
                get_google_oauth_client_secret,
                sync_from_db,
            )

            sync_from_db()
            cid = cid or get_google_oauth_client_id()
            csec = csec or get_google_oauth_client_secret()
        except Exception:
            pass
    return (cid.strip() if cid else None), (csec.strip() if csec else None)


def cobranza_tokens_file_ready() -> bool:
    path = _cobranza_tokens_path()
    if not path or not os.path.isfile(path):
        return False
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("refresh_token"))
    except Exception:
        return False


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
    return {
        "mailbox_target": target,
        "gmail_connected": connected,
        "gmail_profile_email": profile_email,
        "mailbox_match": mailbox_match,
        "ready_for_scan": ready and connected,
        "source_mode": mode,
        "tokens_path": _cobranza_tokens_path(),
        "tokens_file_ready": cobranza_tokens_file_ready(),
        "label_analizados": analizados_label_name(),
        "error": err,
        "mensajes_bd": n_msg,
        "recibos_bd": n_rec,
        "manifest_version": MANIFEST_VERSION,
        "oauth_redirect_hint": (
            f"...{getattr(settings, 'API_V1_STR', '/api/v1')}/auditoria/email/oauth/callback"
        ),
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
    if mode == "single":
        if max_messages < 1 or max_messages > LOT_SIZE_MAX:
            raise ValueError(f"En modo single, maxMessages debe estar entre 1 y {LOT_SIZE_MAX}")
    else:
        if not has_date_bound(criteria):
            raise ValueError(
                "El modo batch exige dateFrom/dateTo o newerThanDays (tope ~32k)."
            )
        if max_messages < 1 or max_messages > 32_000:
            raise ValueError("maxMessages en batch debe estar entre 1 y 32000")


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
    if mode == "single":
        max_messages = max(1, min(int(max_messages or LOT_SIZE_MAX), LOT_SIZE_MAX))
        lot_size = max_messages
    else:
        lot_size = max(1, min(int(lot_size or LOT_SIZE_MAX), LOT_SIZE_MAX))
        max_messages = max(1, min(int(max_messages or 32_000), 32_000))
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


def _apply_analizados(service: Any, message_ids: List[str]) -> int:
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
    for mid in message_ids:
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
    try:
        sync = reserve_gmail_pipeline_sync(db, force=True)
    except GmailPipelineBusyError as e:
        raise RuntimeError(
            "El pipeline Pagos Gmail está ocupado (otra corrida en curso). "
            "Reintenta este lote en unos minutos."
        ) from e
    sync_id, status = run_pipeline(
        db,
        existing_sync_id=sync.id,
        only_message_ids=list(message_ids),
        gmail_credentials=creds,
        defer_autoconciliacion=True,
    )
    return sync_id, status


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

    while lots < max_lots and int(scan.processed_total or 0) < int(scan.max_messages or 0):
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
        accepted_rows: List[Dict[str, Any]] = []
        listed = 0
        rejected = 0

        for ref in refs:
            mid = ref.get("id")
            if not mid:
                continue
            listed += 1
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

        if accepted_rows:
            ids = [str(r["gmail_message_id"]) for r in accepted_rows]
            try:
                sync_id, pipe_status = _run_pagos_pipeline_lot(
                    db, message_ids=ids, creds=creds
                )
            except Exception as e:
                # No avanzar page_token: el mismo lote se reintenta.
                scan.last_error = str(e)[:1000]
                scan.status = "paused"
                scan.page_token = page_token
                scan.updated_at = _utcnow()
                db.add(scan)
                db.commit()
                raise

            outcomes = _sync_item_outcomes(db, sync_id, ids)
            msg_db_map: Dict[str, int] = {}
            for raw in accepted_rows:
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
            db.flush()

            mig = _post_pipeline_cola_recibos(
                db,
                pipe_status,
                sync_id=sync_id,
                candidate_message_ids=ids,
                message_db_by_gmail=msg_db_map,
            )
            listos = list((mig.get("analizados") or {}).get("listos") or [])
            pendientes = list(
                (mig.get("analizados") or {}).get("pendientes_temporal") or []
            )
            labeled = _apply_analizados(service, listos) if listos else 0
            if pendientes:
                logger.warning(
                    "[AUDITORIA_EMAIL] sin ANALIZADOS (sin recibo materializado): %d msgs scan=%s",
                    len(pendientes),
                    scan.id,
                )
            logger.info(
                "[AUDITORIA_EMAIL] lote scan=%s sync=%s status=%s msgs=%d "
                "ANALIZADOS=%d/%d cola_recibos=%s",
                scan.id,
                sync_id,
                pipe_status,
                len(ids),
                labeled,
                len(ids),
                mig.get("materializar") or {},
            )
            scan.processed_total = int(scan.processed_total or 0) + len(accepted_rows)
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
            scan.page_token = None
            scan.status = "complete"
            scan.finished_at = _utcnow()
            scan.last_error = None
            break
        scan.page_token = next_token
        scan.status = "paused"
        scan.last_error = None

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


def _advance_gmail_background(scan_id: int, max_lots: int) -> None:
    from app.core.database import SessionLocal

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
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


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
    import threading

    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
    if scan.status == "complete":
        return _scan_dict(scan)

    if scan.status == "running" and not _scan_looks_stale_running(scan):
        return _scan_dict(scan)
    if _scan_looks_stale_running(scan):
        scan.status = "paused"
        scan.last_error = (
            scan.last_error
            or f"Reanudable: corrida previa sin latido >{SCAN_STALE_RUNNING_MINUTES} min"
        )

    assert_ready_for_scan(db)
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
    return _advance_gmail(db, scan, max_lots)


def auto_advance_paused_scans(
    db: Session,
    *,
    max_scans: int = 1,
    max_lots: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Reanuda escaneos ``paused`` con ``page_token`` (cola batch sin navegador).
    Usado por el scheduler cuando ``AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED``.
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
        "paused": scan.status == "paused" and bool(scan.page_token),
        "labelAnalizados": analizados_label_name(),
    }


def get_scan(db: Session, scan_id: int) -> Dict[str, Any]:
    scan = db.get(AuditoriaEmailScan, scan_id)
    if scan is None:
        raise ValueError("Escaneo no encontrado")
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
    return {
        "mensajes": n_msg,
        "recibos": n_rec,
        "por_ruta": {str(k or "sin_ruta"): int(v) for k, v in by_route.items()},
        "por_clase": {str(k or "sin_clase"): int(v) for k, v in by_class.items()},
        "escaneos_pausados": paused,
        "mailbox": mailbox_target(),
        "label_analizados": analizados_label_name(),
        "gmail_connected": connection_status(db).get("gmail_connected"),
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
    labeled = _apply_analizados(service, listos) if listos else 0
    for msg in rows:
        mid = str(msg.gmail_message_id)
        cerrado = mid in set(listos)
        msg.classify = "digitalizado" if cerrado else "sin_digitalizacion"
        msg.route = "pendiente_aprobacion" if cerrado else "reintentar"
        msg.pipelines_json = {
            "pipelines": [
                {
                    "id": "pagos_gmail.digitalizar",
                    "status": pipe_status,
                    "pagos_sync_id": sync_id,
                    "label": analizados_label_name() if cerrado else None,
                    "cola_recibos": anti,
                    "analizados_aplicado": cerrado,
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

    q_sample = build_gmail_query({"newerThanDays": 7, "attachments": "pdf_or_image"})
    return {
        "manifest_version": MANIFEST_VERSION,
        "flujo": [
            "1. OAuth cobranza@ (tokens aparte)",
            "2. Filtro Gmail (criterios + -label:ANALIZADOS)",
            "3. Lote ≤100 → OCR/digitalizar (defer_autoconciliacion)",
            "4. Materializar cola Recibos (pending)",
            "5. Aprobar en Recibos → validadores + cuotas + cascada",
            "6. Revisión manual → pagos_con_errores",
            f"7. Etiqueta {analizados_label_name()} si hay recibo materializado",
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
                "id": "filtro_gmail_analizados",
                "ok": f"-label:{analizados_label_name()}" in q_sample,
                "detalle": f"Ejemplo q: {q_sample}",
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
                "detalle": "Bandeja: cédula (Clientes) + fecha correo + N adjuntos.",
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
