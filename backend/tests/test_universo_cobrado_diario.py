# -*- coding: utf-8 -*-
"""Recaudo diario de la serie compilada: barras = pagos, no saldo vencido."""
from datetime import date

from app.services.cobranzas.universo_analisis_service import (
    _cuotas_por_bucket_en_dia,
    _punto_serie_desde_metricas,
    _punto_serie_vacio,
    _recaudo_por_bucket_en_dia,
)


def test_recaudo_por_bucket_usa_pagos_del_dia():
    dia = date(2026, 8, 15)
    recaudo = {
        (10, dia): 40.0,
        (11, dia): 10.0,
        (10, date(2026, 8, 16)): 99.0,
    }
    sets = {"1": {10}, "2": {11}, "3": set()}
    out = _recaudo_por_bucket_en_dia(recaudo, sets, dia, ("1", "2", "3"))
    assert out["1"] == 40.0
    assert out["2"] == 10.0
    assert out["3"] == 0.0


def test_recaudo_ignora_prestamo_fuera_del_segmento():
    dia = date(2026, 8, 15)
    recaudo = {(99, dia): 500.0}
    sets = {"1": {10}}
    out = _recaudo_por_bucket_en_dia(recaudo, sets, dia, ("1",))
    assert out["1"] == 0.0


def test_punto_serie_separa_saldo_vencido_y_recaudo():
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
    assert p["cobrado_6"] == 20.0
    assert p["cobrado_7"] == 5.0
    assert p["cobrado_6plus"] == 25.0
    assert p["cobrado_total"] == 105.0
    assert p["cobrado_total"] != p["monto_total"]


def test_punto_serie_vacio_incluye_recaudo():
    p = _punto_serie_vacio(date(2026, 8, 16))
    assert p["cobrado_total"] == 0.0
    assert p["cuotas_total"] == 0
    assert p["monto_total"] == 0.0


def test_cuotas_por_bucket_usa_pagos_del_dia():
    dia = date(2026, 8, 15)
    cuotas = {
        (10, dia): 2,
        (11, dia): 1,
        (10, date(2026, 8, 16)): 9,
    }
    sets = {"1": {10}, "2": {11}, "3": set()}
    out = _cuotas_por_bucket_en_dia(cuotas, sets, dia, ("1", "2", "3"))
    assert out["1"] == 2
    assert out["2"] == 1
    assert out["3"] == 0


def test_punto_serie_incluye_cuotas_cobradas():
    p = _punto_serie_desde_metricas(
        date(2026, 8, 16),
        {"1": 1000.0, "6": 200.0},
        {"1": 10, "6": 2},
        cobrado={"1": 80.0, "6": 20.0},
        cuotas={"1": 3, "6": 1, "7": 2},
    )
    assert p["cuotas_1"] == 3
    assert p["cuotas_6"] == 1
    assert p["cuotas_7"] == 2
    assert p["cuotas_6plus"] == 3
    assert p["cuotas_total"] == 6
    assert p["cobrado_total"] == 100.0


def test_rango_cobrado_mes_ayer_hoy():
    from app.services.cobranzas.universo_analisis_service import (
        _rango_cobrado_lectura,
    )

    hoy = date(2026, 8, 17)
    assert _rango_cobrado_lectura(hoy, hoy) == (hoy, hoy)
    assert _rango_cobrado_lectura(date(2026, 8, 16), hoy) == (
        date(2026, 8, 16),
        date(2026, 8, 16),
    )
    assert _rango_cobrado_lectura(date(2026, 8, 1), hoy) == (
        date(2026, 8, 1),
        hoy,
    )
    assert _rango_cobrado_lectura(date(2026, 6, 1), hoy) == (
        date(2026, 6, 1),
        date(2026, 6, 30),
    )


def test_acumular_cobrado_por_segmento_y_rango():
    from app.services.cobranzas.universo_analisis_service import (
        _acumular_cobrado_en_rango,
    )

    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 2)
    recaudo = {
        (10, d1): 40.0,
        (11, d1): 10.0,
        (10, d2): 5.0,
        (99, d1): 500.0,
    }
    sets_inicio = {"1": {10}, "2": {11}}
    cob, casos = _acumular_cobrado_en_rango(
        recaudo, sets_inicio, d1, d2, ("1", "2")
    )
    assert cob["1"] == 45.0
    assert cob["2"] == 10.0
    assert casos["1"] == 1
    assert casos["2"] == 1
