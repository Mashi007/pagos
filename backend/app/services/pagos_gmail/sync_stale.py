# -*- coding: utf-8 -*-
"""Sync Gmail en estado running huérfano (deploy, worker caído, background sin arrancar)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select, text
from sqlalchemy.orm import Session

from app.models.pagos_gmail_sync import PagosGmailSync

logger = logging.getLogger(__name__)

# Clave fija para pg_advisory_xact_lock: serializa inicio de corrida (evita doble click / race).
GMAIL_PIPELINE_START_LOCK_KEY = 88472931


class GmailPipelineBusyError(Exception):
    """No se pudo reservar una nueva corrida (lock o sync running activa)."""

    def __init__(
        self,
        blocking: Optional[PagosGmailSync] = None,
        *,
        lock_contended: bool = False,
    ) -> None:
        self.blocking = blocking
        self.lock_contended = lock_contended
        super().__init__(
            "lock_contended"
            if lock_contended
            else f"blocking_sync_id={getattr(blocking, 'id', None)}"
        )


def _try_advisory_xact_lock(db: Session) -> bool:
    """Lock transaccional Postgres; se libera al commit/rollback."""
    try:
        return bool(
            db.execute(
                text("SELECT pg_try_advisory_xact_lock(:k)"),
                {"k": GMAIL_PIPELINE_START_LOCK_KEY},
            ).scalar()
        )
    except Exception as exc:
        logger.warning("[PAGOS_GMAIL] advisory lock no disponible: %s", exc)
        return True

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
        rs = getattr(sync, "run_summary", None)
        listed = 0
        if isinstance(rs, dict):
            try:
                listed = int(rs.get("gmail_messages_listed") or 0)
            except (TypeError, ValueError):
                listed = 0
        # Primer correo con imagenes grandes puede tardar >20 min en Gemini sin incrementar contadores.
        if listed > 0:
            return False
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


def reserve_gmail_pipeline_sync(db: Session, *, force: bool = True) -> PagosGmailSync:
    """
    Reconcilia stale, adquiere lock transaccional, verifica que no haya otra corrida
    reciente, inserta fila ``running`` y hace commit.

    Debe llamarse tras validar credenciales/parámetros (el lock solo cubre la ventana crítica).
  """
    reconcile_blocking_running_gmail_sync_if_stale(db)
    if not _try_advisory_xact_lock(db):
        raise GmailPipelineBusyError(lock_contended=True)

    blocking = get_blocking_running_gmail_sync(db)
    if blocking is not None:
        if force and gmail_sync_looks_stale(blocking):
            reconcile_stale_running_gmail_sync(db, blocking)
            blocking = get_blocking_running_gmail_sync(db)
        if blocking is not None:
            raise GmailPipelineBusyError(blocking)

    sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync
