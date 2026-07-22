# -*- coding: utf-8 -*-
"""Menor a 60 / atraso-10-dias: exactamente UNA cuota atrasada."""
from datetime import date, timedelta

from app.services.notificacion_service import (
    MAX_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS,
    MIN_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS,
    item_cumple_regla_menor_60_estricta,
    prestamo_aplica_listado_10_dias_por_cuotas_atrasadas,
)


def test_constantes_una_cuota():
    assert MIN_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS == 1
    assert MAX_CUOTAS_ATRASADAS_PARA_LISTADO_10_DIAS == 1
    assert prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(1) is True
    assert prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(0) is False
    assert prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(2) is False
    assert prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(3) is False
    assert prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(5) is False


def test_rechaza_dos_o_mas_cuotas_atrasadas():
    hoy = date(2026, 7, 21)
    for n in (2, 3, 4, 10):
        item = {
            "cuotas_atrasadas": n,
            "dias_atraso": 10,
            "fecha_vencimiento": (hoy - timedelta(days=10)).isoformat(),
        }
        assert item_cumple_regla_menor_60_estricta(item, hoy) is False, n


def test_acepta_una_cuota_en_rango():
    hoy = date(2026, 7, 21)
    item = {
        "cuotas_atrasadas": 1,
        "dias_atraso": 10,
        "fecha_vencimiento": (hoy - timedelta(days=10)).isoformat(),
    }
    assert item_cumple_regla_menor_60_estricta(item, hoy) is True
