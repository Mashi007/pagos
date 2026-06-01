"""Parsers de monto/fecha del escáner Infopagos (post-Gemini)."""
from datetime import date

from app.services.pagos_gmail.gemini_service import (
    _parse_fecha_escaner_desde_gemini,
    _parse_monto_escaner,
)

REF = date(2026, 5, 31)


def test_parse_monto_escaner_miles_venezolanos():
    assert _parse_monto_escaner("1.500,00") == 1500.0
    assert _parse_monto_escaner("1.500") == 1500.0
    assert _parse_monto_escaner("15.000,50") == 15000.5
    assert _parse_monto_escaner("150,50") == 150.5
    assert _parse_monto_escaner("150.25") == 150.25


def test_parse_fecha_escaner_desde_gemini():
    assert _parse_fecha_escaner_desde_gemini("31/05/2026", REF) == date(2026, 5, 31)
    assert _parse_fecha_escaner_desde_gemini("31/05/26", REF) == date(2026, 5, 31)
    assert _parse_fecha_escaner_desde_gemini("2026-05-31", REF) == date(2026, 5, 31)
    assert _parse_fecha_escaner_desde_gemini(
        "fecha operacion 21/04/2025 sello", REF
    ) == date(2025, 4, 21)
    assert _parse_fecha_escaner_desde_gemini("310526", REF) == date(2026, 5, 31)
    assert _parse_fecha_escaner_desde_gemini("2027-01-01", REF) is None
    assert _parse_fecha_escaner_desde_gemini("", REF) is None
