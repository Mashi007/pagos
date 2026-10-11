"""Tests horario pico export Cobros (Caracas)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.cobros.cobros_operativo_horario import (
    en_horario_pico_export_cobros,
    mensaje_limite_export_pico,
)


def test_en_horario_pico_mediodia_caracas():
    t = datetime(2026, 6, 10, 12, 0, tzinfo=ZoneInfo("America/Caracas"))
    assert en_horario_pico_export_cobros(t) is True


def test_fuera_pico_madrugada_caracas():
    t = datetime(2026, 6, 10, 3, 0, tzinfo=ZoneInfo("America/Caracas"))
    assert en_horario_pico_export_cobros(t) is False


def test_limite_incluye_conteo_en_mensaje():
    msg = mensaje_limite_export_pico(filas=900, max_filas=400)
    assert "900" in msg
    assert "400" in msg
