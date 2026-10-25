# -*- coding: utf-8 -*-
"""Cadencia adaptativa Auditoría Email auto-avance (activo vs idle)."""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.scheduler as sched_mod
from app.core.config import settings
from app.core.scheduler import (
    AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID,
    SCHEDULER_TZ,
    _auditoria_email_advance_interval_minutes,
    _auditoria_email_advance_out_has_work,
    _reschedule_auditoria_email_auto_advance,
    scheduler_is_running,
    start_scheduler,
    stop_scheduler,
)


@pytest.fixture(autouse=True)
def _scheduler_cleanup():
    stop_scheduler()
    yield
    stop_scheduler()


def test_interval_minutes_idle_ge_active(monkeypatch):
    monkeypatch.setattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_INTERVAL_MINUTES", 5)
    monkeypatch.setattr(
        settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_IDLE_INTERVAL_MINUTES", 25
    )
    active, idle = _auditoria_email_advance_interval_minutes()
    assert active == 5
    assert idle == 25


def test_interval_minutes_clamps_idle_below_active(monkeypatch):
    monkeypatch.setattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_INTERVAL_MINUTES", 15)
    monkeypatch.setattr(
        settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_IDLE_INTERVAL_MINUTES", 10
    )
    active, idle = _auditoria_email_advance_interval_minutes()
    assert active == 15
    assert idle == 15


def test_out_has_work_detection():
    assert _auditoria_email_advance_out_has_work(None) is False
    assert _auditoria_email_advance_out_has_work({"ok": True, "advanced": []}) is False
    assert (
        _auditoria_email_advance_out_has_work(
            {"ok": True, "advanced": [{"scan_id": 1, "status": "paused"}]}
        )
        is True
    )
    assert (
        _auditoria_email_advance_out_has_work(
            {"ok": False, "reason": "sin credenciales", "advanced": []}
        )
        is False
    )


def test_scheduler_registers_date_trigger_adaptativo(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_BCV_WIDGET_TASA_JOB", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_DRIVE_CLIENTES_NIGHTLY_0100", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_COBRANZA_GESTORES_EMAIL_JOB", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_PREJUDICIAL", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_ATRASO_10_DIAS", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_DIA_SIGUIENTE", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_COBROS_SANEO_JOB", False, raising=False)
    monkeypatch.setattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_INTERVAL_MINUTES", 5, raising=False)
    monkeypatch.setattr(
        settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_IDLE_INTERVAL_MINUTES", 25, raising=False
    )

    assert not scheduler_is_running()
    start_scheduler()
    assert scheduler_is_running()
    sch = sched_mod._scheduler
    assert sch is not None
    job = sch.get_job(AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID)
    assert job is not None
    assert job.next_run_time is not None
    now = datetime.now(ZoneInfo(SCHEDULER_TZ))
    # Primera corrida ≈ +5 min (activo)
    delta = job.next_run_time - now
    assert timedelta(minutes=4) <= delta <= timedelta(minutes=6)

    _reschedule_auditoria_email_auto_advance(25)
    job2 = sch.get_job(AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID)
    assert job2 is not None and job2.next_run_time is not None
    delta2 = job2.next_run_time - datetime.now(ZoneInfo(SCHEDULER_TZ))
    assert timedelta(minutes=24) <= delta2 <= timedelta(minutes=26)
