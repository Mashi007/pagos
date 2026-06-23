# -*- coding: utf-8 -*-
"""Ejecución del pipeline Gmail fuera del request HTTP (hilo dedicado)."""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.pagos_gmail_sync import PagosGmailSync
from app.services.pagos_gmail.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def run_gmail_pipeline_background(
    sync_id: int,
    scan_filter: str = "all",
    from_email: Optional[str] = None,
    only_message_ids: Optional[list[str]] = None,
    max_messages: Optional[int] = None,
    criterio_remitente: str = "remitente",
) -> None:
    """Ejecuta el pipeline con su propia sesión de BD (no comparte el timeout HTTP de 30s)."""
    db = SessionLocal()
    logger.info(
        "[PAGOS_GMAIL] [ETAPA] Inicio pipeline background sync_id=%s scan_filter=%s from_email=%s criterio=%s only_ids=%d max_messages=%s",
        sync_id,
        scan_filter,
        from_email or "(sin remitente)",
        criterio_remitente,
        len(only_message_ids) if only_message_ids else 0,
        max_messages if max_messages is not None else "(sin tope)",
    )
    try:
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
                    "[PAGOS_GMAIL] [ETAPA] Migración post-run Gmail -> pendientes revisión: migrados=%s omitidos=%s",
                    mig.get("migrados"),
                    mig.get("omitidos"),
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
) -> None:
    """Hilo dedicado: no bloquea el event loop ni el pool del scheduler APScheduler."""
    threading.Thread(
        target=run_gmail_pipeline_background,
        args=(
            sync_id,
            scan_filter,
            from_email,
            only_message_ids,
            max_messages,
            criterio_remitente,
        ),
        name=f"pagos-gmail-pipeline-{sync_id}",
        daemon=True,
    ).start()
