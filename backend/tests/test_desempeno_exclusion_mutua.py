"""Exclusión mutua y buckets excluyentes en stock del dashboard."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.services.desempeno_1_cuota_stock import (
    _stock_1_cuota_at,
    _stock_1_cuota_excluyendo_prejudicial_at,
    _stock_2_cuotas_at,
    _stock_3_cuotas_at,
    _stock_4plus_cuotas_at,
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
    """Cliente con préstamo A en 2 cuotas y B en 1 cuota: B no cuenta en 1 cuota."""
    meta = [
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(200, 7, date(2026, 7, 1)),
        _c(300, 8, date(2026, 7, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}
    assert _stock_1_cuota_at(meta, T0, Z) == {200, 300}
    assert _stock_1_cuota_excluyendo_prejudicial_at(meta, T0, Z) == {300}


def test_excluye_1_cuota_si_cliente_en_4plus():
    meta = [
        _c(100, 7, date(2026, 3, 1)),
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
        _c(200, 7, date(2026, 7, 1)),
        _c(300, 8, date(2026, 7, 1)),
    ]
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
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(200, 7, date(2026, 7, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}


def test_2_cuotas_exige_exactamente_2_totales():
    """Con 3 atrasadas NO entra en segmento 2; va a 3."""
    meta = [
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 7, 10)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == set()
    assert _stock_3_cuotas_at(meta, T0, Z) == {100}
    assert _stock_4plus_cuotas_at(meta, T0, Z) == set()


def test_4plus_ge_4():
    meta = [
        _c(100, 7, date(2026, 3, 1)),
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        _c(100, 7, date(2026, 6, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == set()
    assert _stock_3_cuotas_at(meta, T0, Z) == set()
    assert _stock_4plus_cuotas_at(meta, T0, Z) == {100}


def test_2_cuotas_atraso_min_1():
    """Con atraso >=1 (ya no exige >=60) entra en segmento 2."""
    meta = [
        _c(100, 7, date(2026, 7, 10)),
        _c(100, 7, date(2026, 7, 15)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}
