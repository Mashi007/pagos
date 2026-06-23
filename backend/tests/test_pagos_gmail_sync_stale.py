# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.services.pagos_gmail.sync_stale import (
    STALE_NO_PROGRESS_MINUTES,
    gmail_sync_looks_stale,
    reconcile_stale_running_gmail_sync,
)


def test_gmail_sync_looks_stale_sin_progreso():
    sync = MagicMock()
    sync.status = "running"
    sync.emails_processed = 0
    sync.files_processed = 0
    now = datetime(2026, 6, 23, 13, 0, 0)
    sync.started_at = now - timedelta(minutes=STALE_NO_PROGRESS_MINUTES + 1)
    assert gmail_sync_looks_stale(sync, now=now)


def test_gmail_sync_no_stale_si_hay_progreso_reciente():
    sync = MagicMock()
    sync.status = "running"
    sync.emails_processed = 3
    sync.files_processed = 1
    now = datetime(2026, 6, 23, 13, 0, 0)
    sync.started_at = now - timedelta(minutes=5)
    assert not gmail_sync_looks_stale(sync, now=now)


def test_reconcile_stale_running_marca_error():
    db = MagicMock()
    sync = MagicMock()
    sync.status = "running"
    sync.emails_processed = 0
    sync.files_processed = 0
    now = datetime(2026, 6, 23, 13, 0, 0)
    sync.started_at = now - timedelta(minutes=30)
    sync.id = 99
    assert reconcile_stale_running_gmail_sync(db, sync, now=now) is True
    assert sync.status == "error"
    assert sync.finished_at == now
    db.commit.assert_called_once()
