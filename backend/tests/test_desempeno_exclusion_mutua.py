"""Exclusion mutua y segmentos solo por cantidad de cuotas atrasadas."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.desempeno_1_cuota_stock import (
    _cumple_ventana_6plus,
    _cumple_ventana_segmento,
    _stock_1_cuota_at,
    _stock_1_cuota_excluyendo_prejudicial_at,
    _stock_2_cuotas_at,
    _stock_3_cuotas_at,
    _stock_4_cuotas_at,
    _stock_4plus_cuotas_at,
    _stock_5_cuotas_at,
    _stock_6plus_cuotas_at,
    _stock_exact_n_cuotas_at,
)

Z = ZoneInfo("America/Caracas")
HOY = date(2026, 7, 24)
T0 = datetime.combine(HOY, time(0, 0, 0), tzinfo=Z)


def _c(prestamo_id, cliente_id, fv, paid_at=None):
    return {
        "prestamo_id": prestamo_id,
        "cliente_id": cliente_id,
        "fv": fv,
        "paid_at": paid_at,
    }


def test_excluye_1_cuota_si_mismo_cliente_en_2_cuotas():
    meta = [
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
        _c(200, 7, date(2026, 7, 1)),
        _c(300, 8, date(2026, 7, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}
    assert _stock_1_cuota_at(meta, T0, Z) == {200, 300}
    assert _stock_1_cuota_excluyendo_prejudicial_at(meta, T0, Z) == {300}


def test_excluye_1_cuota_si_cliente_en_4_cuotas():
    meta = [
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
        _c(200, 7, date(2026, 7, 1)),
        _c(300, 8, date(2026, 7, 1)),
    ]
    assert _stock_4_cuotas_at(meta, T0, Z) == {100}
    assert _stock_4plus_cuotas_at(meta, T0, Z) == {100}
    assert _stock_1_cuota_excluyendo_prejudicial_at(meta, T0, Z) == {300}


def test_sin_2_cuotas_no_cambia_1_cuota():
    meta = [
        _c(200, 7, date(2026, 7, 1)),
        _c(300, 8, date(2026, 7, 1)),
    ]
    assert _stock_1_cuota_excluyendo_prejudicial_at(meta, T0, Z) == {200, 300}


def test_2_cuotas_no_se_recorta():
    meta = [
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
        _c(200, 7, date(2026, 7, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}


def test_2_cuotas_exige_exactamente_2_totales():
    meta = [
        _c(100, 7, date(2026, 5, 20)),
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == set()
    assert _stock_3_cuotas_at(meta, T0, Z) == {100}
    assert _stock_4_cuotas_at(meta, T0, Z) == set()


def test_4_cuotas_exactas_sin_tope_dias():
    meta = [
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == set()
    assert _stock_3_cuotas_at(meta, T0, Z) == set()
    assert _stock_4_cuotas_at(meta, T0, Z) == {100}
    assert _stock_5_cuotas_at(meta, T0, Z) == set()
    assert _stock_6plus_cuotas_at(meta, T0, Z) == set()


def test_4_cuotas_sigue_aunque_max_sobre_120():
    meta = [
        _c(100, 7, date(2026, 3, 1)),  # ~145d
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
    ]
    assert _stock_4_cuotas_at(meta, T0, Z) == {100}


def test_5_cuotas_exactas():
    meta = [
        _c(100, 7, date(2026, 3, 10)),
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
    ]
    assert _stock_5_cuotas_at(meta, T0, Z) == {100}
    assert _stock_4_cuotas_at(meta, T0, Z) == set()
    assert _stock_6plus_cuotas_at(meta, T0, Z) == set()


def test_6plus_ge_6():
    meta = [
        _c(100, 7, date(2026, 2, 1)),
        _c(100, 7, date(2026, 3, 1)),
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
        _c(100, 7, date(2026, 6, 15)),
    ]
    assert _stock_6plus_cuotas_at(meta, T0, Z) == {100}
    assert _stock_4_cuotas_at(meta, T0, Z) == set()
    assert _stock_5_cuotas_at(meta, T0, Z) == set()


def test_exact_n_solo_por_conteo():
    assert _cumple_ventana_segmento([10, 20, 30, 40, 50, 60], 6) is True
    assert _cumple_ventana_segmento([10, 20, 30, 40, 50, 200], 6) is True
    assert _cumple_ventana_segmento([10] * 7, 7) is True
    assert _cumple_ventana_segmento([10] * 6 + [220], 7) is True
    assert _cumple_ventana_segmento(list(range(10, 25)), 15) is True
    assert _cumple_ventana_segmento([10] * 5, 6) is False
    assert _cumple_ventana_6plus([10] * 6) is True
    assert _cumple_ventana_6plus([10] * 5) is False


def test_6_cuotas_exactas_incluye_atraso_alto():
    meta = [
        _c(100, 7, date(2026, 1, 1)),
        _c(100, 7, date(2026, 2, 1)),
        _c(100, 7, date(2026, 3, 1)),
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
    ]
    assert _stock_exact_n_cuotas_at(meta, T0, Z, 6) == {100}
    assert _stock_6plus_cuotas_at(meta, T0, Z) == {100}


def test_2_cuotas_con_atraso_corto():
    meta = [
        _c(100, 7, date(2026, 7, 10)),
        _c(100, 7, date(2026, 7, 15)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}


def test_1_cuota_desde_dia_1():
    meta = [_c(100, 7, date(2026, 7, 23))]
    assert _stock_1_cuota_at(meta, T0, Z) == {100}


def test_1_cuota_incluye_mas_de_30_dias():
    meta = [_c(100, 7, date(2026, 6, 14))]
    assert _stock_1_cuota_at(meta, T0, Z) == {100}


def test_2_cuotas_incluye_max_sobre_60():
    meta = [
        _c(100, 7, date(2026, 5, 5)),
        _c(100, 7, date(2026, 6, 15)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}


def test_10_cuotas_es_segmento_10():
    meta = [_c(100, 7, HOY - timedelta(days=i + 1)) for i in range(10)]
    assert _stock_exact_n_cuotas_at(meta, T0, Z, 10) == {100}
    assert _stock_exact_n_cuotas_at(meta, T0, Z, 9) == set()
