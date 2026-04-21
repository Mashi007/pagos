# -*- coding: utf-8 -*-
"""
Registro de jobs APScheduler: ids esperados tras start_scheduler (sin Gmail).

Ejecutar desde backend/:
  pytest tests/test_scheduler_jobs_registry.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.scheduler as sched_mod
from app.core.config import settings
from app.core.scheduler import (
    PAGOS_GMAIL_PENDING_SCAN_JOB_ID,
    scheduler_is_running,
    start_scheduler,
    stop_scheduler,
)


@pytest.fixture(autouse=True)
def _scheduler_cleanup():
    stop_scheduler()
    yield
    stop_scheduler()


def test_scheduler_registers_core_jobs(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True, raising=False)

    assert not scheduler_is_running()
    start_scheduler()
    assert scheduler_is_running()
    sch = sched_mod._scheduler
    assert sch is not None
    ids = {j.id for j in sch.get_jobs()}
    for jid in (
        "finiquito_refresh_lun_sab_0100",
        "finiquito_refresh_lun_sab_1300",
        "hoja_drive_conciliacion_dom_0120",
        "hoja_drive_conciliacion_mie_0120",
        "auditoria_cartera_prestamos_0300",
        "limpiar_estado_cuenta_codigos",
        "drive_clientes_candidatos_cache_0405",
        "abonos_drive_cuotas_cache_dom_0435",
        "prestamo_candidatos_drive_0445",
        "fecha_entrega_q_aprobacion_cache_dom_0510",
    ):
        assert jid in ids, (jid, sorted(ids))
    assert PAGOS_GMAIL_PENDING_SCAN_JOB_ID not in ids
    assert "notificaciones_pago_2_dias_antes_diario" not in ids

    stop_scheduler()
    assert not scheduler_is_running()


def test_scheduler_registers_cron_2_dias_antes_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", True, raising=False)
    monkeypatch.setattr(settings, "CRON_2_DIAS_ANTES_HOUR", 8, raising=False)
    monkeypatch.setattr(settings, "CRON_2_DIAS_ANTES_MINUTE", 15, raising=False)

    assert not scheduler_is_running()
    start_scheduler()
    sch = sched_mod._scheduler
    assert sch is not None
    ids = {j.id for j in sch.get_jobs()}
    assert "notificaciones_pago_2_dias_antes_diario" in ids
    j = sch.get_job("notificaciones_pago_2_dias_antes_diario")
    assert j is not None
    assert "08:15" in (j.name or "")

    stop_scheduler()


def test_scheduler_wrap_logs_duration(caplog, monkeypatch):
    """El wrapper de timing ejecuta el cuerpo y deja rastro job_start/job_end."""
    import logging

    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)

    caplog.set_level(logging.INFO, logger="app.core.scheduler")
    start_scheduler()
    wrapped = sched_mod._wrap_job_with_timing("probe", lambda: None)
    wrapped()
    stop_scheduler()
    joined = " ".join(rec.message for rec in caplog.records if rec.name == "app.core.scheduler")
    assert "job_start id=probe" in joined
    assert "job_end id=probe" in joined
    assert "duration_ms=" in joined
