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
    BCV_WIDGET_TASA_JOB_ID,
    BCV_WIDGET_TASA_TIMES,
    PAGOS_GMAIL_PENDING_SCAN_JOB_ID,
    PAGOS_GMAIL_SCAN_WEEKDAY_HOURS,
    PAGOS_GMAIL_SCAN_WEEKEND_HOURS,
    RECIBOS_CONCILIACION_EMAIL_JOB_ID,
    RECIBOS_CRON_MINUTE,
    RECIBOS_CRON_WEEKDAY_HOURS,
    RECIBOS_CRON_WEEKEND_HOURS,
    scheduler_is_running,
    start_scheduler,
    stop_scheduler,
)


def _cron_field_str(trigger, name: str) -> str:
    field = next((f for f in trigger.fields if f.name == name), None)
    return str(field) if field is not None else ""


@pytest.fixture(autouse=True)
def _scheduler_cleanup():
    stop_scheduler()
    yield
    stop_scheduler()


def test_scheduler_registers_core_jobs(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_BCV_WIDGET_TASA_JOB", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False, raising=False)

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
    assert BCV_WIDGET_TASA_JOB_ID not in ids
    assert "notificaciones_pago_2_dias_antes_diario" not in ids
    assert "recibos_conciliacion_email_diario" not in ids

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


def test_scheduler_registers_recibos_cron_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", True, raising=False)
    monkeypatch.setattr(settings, "RECIBOS_CRON_HOUR_START", 6, raising=False)
    monkeypatch.setattr(settings, "RECIBOS_CRON_HOUR_END", 10, raising=False)
    monkeypatch.setattr(settings, "RECIBOS_CRON_WEEKEND_HOUR_START", 8, raising=False)
    monkeypatch.setattr(settings, "RECIBOS_CRON_WEEKEND_HOUR_END", 20, raising=False)
    monkeypatch.setattr(settings, "RECIBOS_CRON_MINUTE", 30, raising=False)

    assert not scheduler_is_running()
    start_scheduler()
    sch = sched_mod._scheduler
    assert sch is not None
    ids = {j.id for j in sch.get_jobs()}
    assert RECIBOS_CONCILIACION_EMAIL_JOB_ID in ids
    j = sch.get_job(RECIBOS_CONCILIACION_EMAIL_JOB_ID)
    assert j is not None
    assert "06:30-10:30" in (j.name or "")
    assert "08:30-20:30" in (j.name or "")
    subs = getattr(j.trigger, "triggers", None) or []
    assert len(subs) == 2
    weekday_hours = None
    weekend_hours = None
    for t in subs:
        dow = _cron_field_str(t, "day_of_week").lower()
        hour = _cron_field_str(t, "hour")
        minute = _cron_field_str(t, "minute")
        assert minute == "30"
        if "mon" in dow or "fri" in dow:
            weekday_hours = hour
        elif "sat" in dow or "sun" in dow:
            weekend_hours = hour
    assert weekday_hours == RECIBOS_CRON_WEEKDAY_HOURS
    assert weekend_hours == RECIBOS_CRON_WEEKEND_HOURS

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


def test_scheduler_registers_gmail_unlabeled_scan_caracas_slots(monkeypatch):
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)

    start_scheduler()
    sch = sched_mod._scheduler
    assert sch is not None
    j = sch.get_job(PAGOS_GMAIL_PENDING_SCAN_JOB_ID)
    assert j is not None
    subs = getattr(j.trigger, "triggers", None) or []
    assert len(subs) == 2
    weekday_hours = None
    weekend_hours = None
    for t in subs:
        dow = _cron_field_str(t, "day_of_week").lower()
        hour = _cron_field_str(t, "hour")
        minute = _cron_field_str(t, "minute")
        assert minute in ("0", "*")
        if "mon" in dow or "fri" in dow:
            weekday_hours = hour
        elif "sat" in dow or "sun" in dow:
            weekend_hours = hour
    assert weekday_hours == PAGOS_GMAIL_SCAN_WEEKDAY_HOURS
    assert weekend_hours == PAGOS_GMAIL_SCAN_WEEKEND_HOURS
    stop_scheduler()


def test_scheduler_registers_bcv_widget_tasa_slots(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BCV_WIDGET_TASA_JOB", True, raising=False)
    monkeypatch.setattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", False, raising=False)

    start_scheduler()
    sch = sched_mod._scheduler
    assert sch is not None
    j = sch.get_job(BCV_WIDGET_TASA_JOB_ID)
    assert j is not None
    subs = getattr(j.trigger, "triggers", None) or []
    got = set()
    for t in subs:
        hour_f = next((f for f in t.fields if f.name == "hour"), None)
        min_f = next((f for f in t.fields if f.name == "minute"), None)
        assert hour_f is not None and min_f is not None
        hours = [int(x) for x in str(hour_f).split(",") if x.isdigit()]
        mins = [int(x) for x in str(min_f).split(",") if x.isdigit()]
        if hours and mins:
            got.add((hours[0], mins[0]))
    assert got == set(BCV_WIDGET_TASA_TIMES)
    assert (16, 0) in got
    assert (17, 30) in got
    assert (20, 0) not in got
    for t in subs:
        dow_f = next((f for f in t.fields if f.name == "day_of_week"), None)
        assert dow_f is not None
        dow = str(dow_f).lower()
        assert "sat" not in dow and "sun" not in dow
    stop_scheduler()
