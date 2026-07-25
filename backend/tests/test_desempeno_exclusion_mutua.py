"""Exclusión mutua en stock del gráfico 1 cuota (dashboard)."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.services.desempeno_1_cuota_stock import (
    _stock_1_cuota_at,
    _stock_1_cuota_excluyendo_prejudicial_at,
    _stock_2_cuotas_at,
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
        # Prestamo 100, cliente 7: 2 cuotas >=60d
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
        # Prestamo 200, mismo cliente 7: 1 cuota 6-59d
        _c(200, 7, date(2026, 7, 1)),
        # Prestamo 300, otro cliente: 1 cuota sola
        _c(300, 8, date(2026, 7, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}
    assert _stock_1_cuota_at(meta, T0, Z) == {200, 300}
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
    """Con 3 atrasadas (aunque 2 sean >=60) NO entra en segmento 2 cuotas."""
    meta = [
        _c(100, 7, date(2026, 4, 1)),   # ~114d
        _c(100, 7, date(2026, 5, 1)),   # ~84d
        _c(100, 7, date(2026, 7, 10)),  # ~14d atrasada pero <60
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == set()


def test_2_cuotas_ambas_ge_60():
    meta = [
        _c(100, 7, date(2026, 4, 1)),
        _c(100, 7, date(2026, 5, 1)),
    ]
    assert _stock_2_cuotas_at(meta, T0, Z) == {100}
