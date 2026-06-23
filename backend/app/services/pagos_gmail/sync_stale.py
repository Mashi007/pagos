# -*- coding: utf-8 -*-
"""Sync Gmail en estado running huérfano (deploy, worker caído, background sin arrancar)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.pagos_gmail_sync import PagosGmailSync

logger = logging.getLogger(__name__)

# Sin correos/archivos tras este tiempo → probablemente el background nunca corrió.
STALE_NO_PROGRESS_MINUTES = 20
# Tope absoluto aunque haya progreso parcial (worker interrumpido a mitad).
STALE_MAX_RUNNING_MINUTES = 110
BLOCKING_RUNNING_WINDOW_HOURS = 2


def get_blocking_running_gmail_sync(db: Session) -> Optional[PagosGmailSync]:
    """Sync en running iniciada en las últimas 2 h (bloquea run-now)."""
    cutoff = datetime.utcnow() - timedelta(hours=BLOCKING_RUNNING_WINDOW_HOURS)
    return db.execute(
        select(PagosGmailSync).where(
            and_(
                PagosGmailSync.status == "running",
                PagosGmailSync.started_at >= cutoff,
            )
        ).limit(1)
    ).scalars().first()


def _age_minutes(sync: PagosGmailSync, now: datetime) -> float:
    started = sync.started_at
    if started is None:
        return float(STALE_MAX_RUNNING_MINUTES + 1)
    return max(0.0, (now - started).total_seconds() / 60.0)


def gmail_sync_looks_stale(sync: PagosGmailSync, *, now: Optional[datetime] = None) -> bool:
    """True si la fila running parece abandonada (sin actividad o demasiado antigua)."""
    if (sync.status or "").strip().lower() != "running":
        return False
    now = now or datetime.utcnow()
    age = _age_minutes(sync, now)
    emails = int(sync.emails_processed or 0)
    files = int(sync.files_processed or 0)
    if emails == 0 and files == 0 and age >= STALE_NO_PROGRESS_MINUTES:
        return True
    if age >= STALE_MAX_RUNNING_MINUTES:
        return True
    return False


def reconcile_stale_running_gmail_sync(
    db: Session,
    sync: PagosGmailSync,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """
    Marca error una sync running huérfana. Retorna True si se reconcilió.
    No hace commit si no hubo cambio.
    """
    if not gmail_sync_looks_stale(sync, now=now):
        return False
    now = now or datetime.utcnow()
    emails = int(sync.emails_processed or 0)
    files = int(sync.files_processed or 0)
    if emails == 0 and files == 0:
        msg = (
            "Proceso Gmail sin actividad (0 correos procesados). Suele ocurrir tras un reinicio "
            "del servidor en Render. Puede reintentar con «Procesar manualmente»."
        )
    else:
        msg = (
            "Proceso Gmail interrumpido en el servidor (tiempo máximo superado). "
            "Reintente con «Procesar manualmente»."
        )
    sync.status = "error"
    sync.finished_at = now
    sync.error_message = msg[:2000]
    db.commit()
    logger.warning(
        "[PAGOS_GMAIL] Sync running huérfana reconciliada sync_id=%s emails=%s files=%s started_at=%s",
        sync.id,
        emails,
        files,
        sync.started_at,
    )
    return True


def reconcile_blocking_running_gmail_sync_if_stale(db: Session) -> Optional[PagosGmailSync]:
    """Si hay una sync running bloqueante y está huérfana, la marca error."""
    blocking = get_blocking_running_gmail_sync(db)
    if blocking is None:
        return None
    if reconcile_stale_running_gmail_sync(db, blocking):
        return blocking
    return None
