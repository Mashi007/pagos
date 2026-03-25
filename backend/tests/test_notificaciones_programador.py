"""Tests para hora programador (parseo y clave de deduplicacion)."""

from app.services.notificaciones_programador import (
    _slot_key,
    parse_programador_hm,
)


def test_parse_programador_default():
    assert parse_programador_hm(None) == (1, 0)
    assert parse_programador_hm("") == (1, 0)
    assert parse_programador_hm("   ") == (1, 0)


def test_parse_programador_hh_mm():
    assert parse_programador_hm("19:00") == (19, 0)
    assert parse_programador_hm("01:30") == (1, 30)
    assert parse_programador_hm("7:05") == (7, 5)


def test_parse_programador_wrap():
    assert parse_programador_hm("25:00") == (1, 0)
    assert parse_programador_hm("10:99") == (10, 39)


def test_slot_key():
    assert _slot_key("2026-03-24", (19, 5)) == "2026-03-24|19:05"
