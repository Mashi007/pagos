# -*- coding: utf-8 -*-
from app.services.notificaciones_cron_2_dias_antes_job import debe_omitir_cron_por_estado_persistido


def test_debe_omitir_si_ok_misma_fecha():
    assert debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-21", "estado": "ok"},
        "2026-04-21",
    )


def test_debe_omitir_si_error_misma_fecha():
    assert debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-21", "estado": "error"},
        "2026-04-21",
    )


def test_no_omitir_fecha_distinta():
    assert not debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-20", "estado": "ok"},
        "2026-04-21",
    )


def test_no_omitir_estado_no_terminal():
    assert not debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-21", "estado": "running"},
        "2026-04-21",
    )
