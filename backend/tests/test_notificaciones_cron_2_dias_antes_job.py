# -*- coding: utf-8 -*-
from app.services.notificaciones_cron_2_dias_antes_job import (
    debe_omitir_cron_por_estado_persistido,
)


def test_debe_omitir_si_ok_mismo_slot():
    assert debe_omitir_cron_por_estado_persistido(
        {
            "fecha_referencia_caracas": "2026-04-21",
            "slots": {"07:15": {"estado": "ok"}},
        },
        "2026-04-21",
        "07:15",
    )


def test_debe_omitir_si_error_mismo_slot():
    assert debe_omitir_cron_por_estado_persistido(
        {
            "fecha_referencia_caracas": "2026-04-21",
            "slots": {"18:15": {"estado": "error"}},
        },
        "2026-04-21",
        "18:15",
    )


def test_no_omitir_otro_slot_mismo_dia():
    assert not debe_omitir_cron_por_estado_persistido(
        {
            "fecha_referencia_caracas": "2026-04-21",
            "slots": {"07:15": {"estado": "ok"}},
        },
        "2026-04-21",
        "18:15",
    )


def test_no_omitir_fecha_distinta():
    assert not debe_omitir_cron_por_estado_persistido(
        {
            "fecha_referencia_caracas": "2026-04-20",
            "slots": {"07:15": {"estado": "ok"}},
        },
        "2026-04-21",
        "07:15",
    )


def test_legacy_sin_slots_no_bloquea_con_slot():
    assert not debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-21", "estado": "ok"},
        "2026-04-21",
        "07:15",
    )


def test_legacy_sin_slot_omite_estado_diario():
    assert debe_omitir_cron_por_estado_persistido(
        {"fecha_referencia_caracas": "2026-04-21", "estado": "ok"},
        "2026-04-21",
        "",
    )
