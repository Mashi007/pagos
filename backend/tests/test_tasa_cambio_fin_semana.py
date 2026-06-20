"""Reglas sábado/domingo: copia del viernes anterior, sin ingreso obligatorio."""
from datetime import date

import pytest

from app.services.tasa_cambio_service import (
    debe_ingresar_tasa,
    es_fin_de_semana_caracas,
    ultimo_viernes_anterior,
)


def test_es_fin_de_semana_solo_sabado_y_domingo():
    assert es_fin_de_semana_caracas(date(2026, 6, 20)) is True  # sábado
    assert es_fin_de_semana_caracas(date(2026, 6, 21)) is True  # domingo
    assert es_fin_de_semana_caracas(date(2026, 6, 19)) is False  # viernes
    assert es_fin_de_semana_caracas(date(2026, 6, 22)) is False  # lunes


def test_ultimo_viernes_anterior():
    assert ultimo_viernes_anterior(date(2026, 6, 20)) == date(2026, 6, 19)
    assert ultimo_viernes_anterior(date(2026, 6, 21)) == date(2026, 6, 19)


def test_ultimo_viernes_anterior_rechaza_dia_laboral():
    with pytest.raises(ValueError):
        ultimo_viernes_anterior(date(2026, 6, 19))


def test_debe_ingresar_false_en_fin_de_semana(monkeypatch):
    import app.services.tasa_cambio_service as svc

    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: date(2026, 6, 20))
    assert es_fin_de_semana_caracas() is True
    assert debe_ingresar_tasa() is False
