# -*- coding: utf-8 -*-
"""Regla PREJUDICIAL innegociable: >=60 dias y >=2 cuotas."""
from datetime import date, timedelta

from app.services.notificacion_service import (
    MIN_DIAS_ATRASO_PREJUDICIAL,
    PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60,
    item_cumple_regla_prejudicial_estricta,
)


def test_constantes_innegociables():
    assert MIN_DIAS_ATRASO_PREJUDICIAL == 60
    assert PREJUDICIAL_MIN_CUOTAS_CON_ATRASO_60 == 2


def test_rechaza_una_sola_cuota():
    hoy = date(2026, 7, 21)
    item = {
        "total_cuotas_atrasadas": 1,
        "dias_atraso": 90,
        "fecha_vencimiento": (hoy - timedelta(days=90)).isoformat(),
    }
    assert item_cumple_regla_prejudicial_estricta(item, hoy) is False


def test_rechaza_menos_de_60_dias():
    hoy = date(2026, 7, 21)
    item = {
        "total_cuotas_atrasadas": 3,
        "dias_atraso": 59,
        "fecha_vencimiento": (hoy - timedelta(days=59)).isoformat(),
    }
    assert item_cumple_regla_prejudicial_estricta(item, hoy) is False


def test_acepta_60_dias_y_2_cuotas():
    hoy = date(2026, 7, 21)
    item = {
        "total_cuotas_atrasadas": 2,
        "dias_atraso": 60,
        "fecha_vencimiento": (hoy - timedelta(days=60)).isoformat(),
    }
    assert item_cumple_regla_prejudicial_estricta(item, hoy) is True


def test_acepta_por_fecha_sin_dias_atraso():
    hoy = date(2026, 7, 21)
    item = {
        "total_cuotas_atrasadas": 5,
        "fecha_vencimiento": (hoy - timedelta(days=61)).isoformat(),
    }
    assert item_cumple_regla_prejudicial_estricta(item, hoy) is True
