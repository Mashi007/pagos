# -*- coding: utf-8 -*-
"""Tests de detección de sync Gmail running huérfana."""
from datetime import datetime, timedelta

from app.models.pagos_gmail_sync import PagosGmailSync
from app.services.pagos_gmail.sync_stale import (
    STALE_MAX_RUNNING_MINUTES,
    STALE_NO_PROGRESS_MINUTES,
    gmail_sync_looks_stale,
)


def _sync(
    *,
    status: str = "running",
    emails: int = 0,
    files: int = 0,
    minutes_ago: float = 0,
    run_summary: dict | None = None,
) -> PagosGmailSync:
    now = datetime.utcnow()
    return PagosGmailSync(
        id=1,
        status=status,
        emails_processed=emails,
        files_processed=files,
        started_at=now - timedelta(minutes=minutes_ago),
        run_summary=run_summary,
    )


def test_stale_when_zero_progress_after_20_minutes():
    sync = _sync(minutes_ago=STALE_NO_PROGRESS_MINUTES + 1)
    assert gmail_sync_looks_stale(sync) is True


def test_not_stale_when_messages_listed_but_zero_counters():
    sync = _sync(
        minutes_ago=STALE_NO_PROGRESS_MINUTES + 5,
        run_summary={"gmail_messages_listed": 45, "pipeline_phase": "processing"},
    )
    assert gmail_sync_looks_stale(sync) is False


def test_stale_when_max_running_minutes_exceeded():
    sync = _sync(
        emails=3,
        files=2,
        minutes_ago=STALE_MAX_RUNNING_MINUTES + 1,
        run_summary={"gmail_messages_listed": 45},
    )
    assert gmail_sync_looks_stale(sync) is True


def test_not_stale_for_success_status():
    sync = _sync(status="success", minutes_ago=STALE_MAX_RUNNING_MINUTES + 10)
    assert gmail_sync_looks_stale(sync) is False
