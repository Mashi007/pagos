# -*- coding: utf-8 -*-
"""Ejecucion del pipeline Gmail fuera del request HTTP (hilo dedicado)."""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.pagos_gmail_sync import PagosGmailSync
from app.services.pagos_gmail.sync_stale import (
    GmailPipelineBusyError,
    reserve_gmail_pipeline_sync,
)

logger = logging.getLogger(__name__)

# Reanudacion automatica tras corte (deploy/SIGTERM/error): cada ronda lista de nuevo
# y omite correos ya etiquetados; maximo de rondas para no buclear indefinidamente.
AUTO_CONTINUE_MAX_ROUNDS = 15


def _run_summary_dict(sync: PagosGmailSync | None) -> dict[str, Any]:
    if sync is None:
        return {}
    rs = sync.run_summary
    return rs if isinstance(rs, dict) else {}


def _partial_inbox_progress(sync: PagosGmailSync | None) -> tuple[int, int]:
    """(emails_processed, gmail_messages_listed) de la ultima corrida."""
    if sync is None:
        return 0, 0
    rs = _run_summary_dict(sync)
    listed = int(rs.get("gmail_messages_listed") or 0)
    emails = int(sync.emails_processed or 0)
    return emails, listed


def should_auto_continue_gmail_pipeline(
    sync: PagosGmailSync | None,
    final_status: str,
    *,
    continue_round: int,
    only_message_ids: Optional[list[str]],
    max_messages: Optional[int],
) -> bool:
    if continue_round >= AUTO_CONTINUE_MAX_ROUNDS:
        return False
    if only_message_ids or max_messages is not None:
        return False
    if final_status != "error":
        return False
    emails, listed = _partial_inbox_progress(sync)
    return listed > 0 and 0 < emails < listed


def _schedule_auto_continue_round(
    parent_sync_id: int,
    *,
    scan_filter: str,
    from_email: Optional[str],
    criterio_remitente: str,
    continue_round: int,
) -> None:
    new_db = SessionLocal()
    try:
        sync_new = reserve_gmail_pipeline_sync(new_db, force=True)
        new_id = sync_new.id
    except GmailPipelineBusyError:
        logger.warning(
            "[PAGOS_GMAIL] Auto-continue: pipeline ocupado (parent_sync_id=%s ronda=%d); "
            "el operador puede pulsar de nuevo Actualizar Gmail",
            parent_sync_id,
            continue_round,
        )
        return
    finally:
        new_db.close()

    logger.info(
        "[PAGOS_GMAIL] Auto-continue ronda %d/%d: parent_sync_id=%s -> sync_id=%s scan_filter=%s",
        continue_round,
        AUTO_CONTINUE_MAX_ROUNDS,
        parent_sync_id,
        new_id,
        scan_filter,
    )
    schedule_gmail_pipeline_background(
        new_id,
        scan_filter=scan_filter,
        from_email=from_email,
        only_message_ids=None,
        max_messages=None,
        criterio_remitente=criterio_remitente,
        continue_round=continue_round,
        parent_sync_id=parent_sync_id,
    )


def _maybe_auto_continue_after_run(
    db,
    sync_id: int,
    final_status: str,
    *,
    scan_filter: str,
    from_email: Optional[str],
    only_message_ids: Optional[list[str]],
    max_messages: Optional[int],
    criterio_remitente: str,
    continue_round: int,
) -> None:
    sync = (
        db.execute(select(PagosGmailSync).where(PagosGmailSync.id == sync_id))
        .scalars()
        .first()
    )
    if not should_auto_continue_gmail_pipeline(
        sync,
        final_status,
        continue_round=continue_round,
        only_message_ids=only_message_ids,
        max_messages=max_messages,
    ):
        return
    emails, listed = _partial_inbox_progress(sync)
    logger.warning(
        "[PAGOS_GMAIL] Progreso parcial %d/%d (sync_id=%s); programando reanudacion automatica",
        emails,
        listed,
        sync_id,
    )
    _schedule_auto_continue_round(
        sync_id,
        scan_filter=scan_filter,
        from_email=from_email,
        criterio_remitente=criterio_remitente,
        continue_round=continue_round + 1,
    )


def run_gmail_pipeline_background(
    sync_id: int,
    scan_filter: str = "all",
    from_email: Optional[str] = None,
    only_message_ids: Optional[list[str]] = None,
    max_messages: Optional[int] = None,
    criterio_remitente: str = "remitente",
    *,
    continue_round: int = 0,
    parent_sync_id: Optional[int] = None,
) -> None:
    """Ejecuta el pipeline con su propia sesion de BD (no comparte el timeout HTTP de 30s)."""
    db = SessionLocal()
    final_status = "error"
    logger.info(
        "[PAGOS_GMAIL] [ETAPA] Inicio pipeline background sync_id=%s scan_filter=%s from_email=%s "
        "criterio=%s only_ids=%d max_messages=%s continue_round=%d parent_sync_id=%s",
        sync_id,
        scan_filter,
        from_email or "(sin remitente)",
        criterio_remitente,
        len(only_message_ids) if only_message_ids else 0,
        max_messages if max_messages is not None else "(sin tope)",
        continue_round,
        parent_sync_id or "(raiz)",
    )
    try:
        from app.services.pagos_gmail.pipeline import run_pipeline

        _, final_status = run_pipeline(
            db,
            existing_sync_id=sync_id,
            scan_filter=scan_filter,
            from_email=from_email,
            only_message_ids=only_message_ids,
            max_messages=max_messages,
            criterio_remitente=criterio_remitente,
        )
        if final_status == "success":
            from app.api.v1.endpoints.pagos_gmail.routes import (
                _migrar_pendientes_gmail_a_con_errores_core,
            )

            mig = _migrar_pendientes_gmail_a_con_errores_core(db)
            if int(mig.get("migrados", 0) or 0) > 0:
                logger.info(
                    "[PAGOS_GMAIL] [ETAPA] Migracion post-run Gmail -> pendientes revision: migrados=%s omitidos=%s",
                    mig.get("migrados"),
                    mig.get("omitidos"),
                )
        _maybe_auto_continue_after_run(
            db,
            sync_id,
            final_status,
            scan_filter=scan_filter,
            from_email=from_email,
            only_message_ids=only_message_ids,
            max_messages=max_messages,
            criterio_remitente=criterio_remitente,
            continue_round=continue_round,
        )
    except Exception as e:
        logger.info("[PAGOS_GMAIL] [ETAPA] Pipeline finalizado sync_id=%s", sync_id)
        logger.exception(
            "[PAGOS_GMAIL] [ETAPA] Error en background pipeline (sync_id=%s): %s",
            sync_id,
            e,
        )
        try:
            sync = (
                db.execute(select(PagosGmailSync).where(PagosGmailSync.id == sync_id))
                .scalars()
                .first()
            )
            if sync and sync.status == "running":
                sync.status = "error"
                sync.finished_at = datetime.utcnow()
                sync.error_message = str(e)[:2000]
                db.commit()
            _maybe_auto_continue_after_run(
                db,
                sync_id,
                "error",
                scan_filter=scan_filter,
                from_email=from_email,
                only_message_ids=only_message_ids,
                max_messages=max_messages,
                criterio_remitente=criterio_remitente,
                continue_round=continue_round,
            )
        except Exception:
            pass
    finally:
        db.close()


def schedule_gmail_pipeline_background(
    sync_id: int,
    scan_filter: str = "all",
    from_email: Optional[str] = None,
    only_message_ids: Optional[list[str]] = None,
    max_messages: Optional[int] = None,
    criterio_remitente: str = "remitente",
    *,
    continue_round: int = 0,
    parent_sync_id: Optional[int] = None,
) -> None:
    """Hilo dedicado: no bloquea el event loop ni el pool del scheduler APScheduler."""
    threading.Thread(
        target=run_gmail_pipeline_background,
        kwargs={
            "sync_id": sync_id,
            "scan_filter": scan_filter,
            "from_email": from_email,
            "only_message_ids": only_message_ids,
            "max_messages": max_messages,
            "criterio_remitente": criterio_remitente,
            "continue_round": continue_round,
            "parent_sync_id": parent_sync_id,
        },
        name=f"pagos-gmail-pipeline-{sync_id}",
        daemon=True,
    ).start()
