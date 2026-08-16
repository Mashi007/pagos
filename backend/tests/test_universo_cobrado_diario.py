# -*- coding: utf-8 -*-
"""Cobrado diario de la serie compilada: barras = dinero del dia, no stock."""
from datetime import date
from types import SimpleNamespace

from app.services.cobranzas.universo_analisis_service import (
    _cobrado_cuota_en_dia,
    _punto_serie_desde_metricas,
    _punto_serie_vacio,
)


def test_cobrado_cuota_usa_evento_del_dia():
    hoy = date(2026, 8, 16)
    dia = date(2026, 8, 15)
    cuota = SimpleNamespace(id=1, monto=100, fecha_pago=None, total_pagado=60)
    eventos = [(date(2026, 8, 10), 20.0), (dia, 40.0)]
    assert _cobrado_cuota_en_dia(cuota, eventos, dia, hoy) == 40.0


def test_cobrado_cuota_fecha_pago_cierra_resto():
    hoy = date(2026, 8, 16)
    dia = date(2026, 8, 15)
    cuota = SimpleNamespace(id=1, monto=100, fecha_pago=dia, total_pagado=100)
    eventos = [(date(2026, 8, 10), 30.0)]
    assert _cobrado_cuota_en_dia(cuota, eventos, dia, hoy) == 70.0


def test_cobrado_cuota_dia_sin_movimiento_es_cero():
    hoy = date(2026, 8, 16)
    dia = date(2026, 8, 15)
    cuota = SimpleNamespace(id=1, monto=100, fecha_pago=date(2026, 8, 10), total_pagado=100)
    eventos = [(date(2026, 8, 10), 100.0)]
    assert _cobrado_cuota_en_dia(cuota, eventos, dia, hoy) == 0.0


def test_punto_serie_separa_stock_y_cobrado():
    p = _punto_serie_desde_metricas(
        date(2026, 8, 16),
        {"1": 1000.0, "6": 200.0, "7": 50.0},
        {"1": 10, "6": 2, "7": 1},
        cobrado={"1": 80.0, "6": 20.0, "7": 5.0},
    )
    assert p["monto_1"] == 1000.0
    assert p["monto_6plus"] == 250.0
    assert p["monto_total"] == 1250.0
    assert p["cobrado_1"] == 80.0
    assert p["cobrado_6plus"] == 25.0
    assert p["cobrado_total"] == 105.0


def test_punto_serie_vacio_incluye_cobrado():
    p = _punto_serie_vacio(date(2026, 8, 16))
    assert p["cobrado_total"] == 0.0
    assert p["monto_total"] == 0.0
