"""Regresión: sync Impagas→Drive Cuotas debe ser idempotente."""
from __future__ import annotations

from app.services.cuotas_hoja_periodo_sync import (
    _monto_alineado,
    _valores_sync_desde_corte,
)


def test_valores_sync_desde_corte_usa_absolutos_bd():
    cuotas, monto = _valores_sync_desde_corte({"cuotas_bd": 3, "monto_bd": 150.5})
    assert cuotas == 3
    assert monto == 150.5


def test_valores_sync_desde_corte_cero_limpia_monto():
    cuotas, monto = _valores_sync_desde_corte({"cuotas_bd": 0, "monto_bd": 99.0})
    assert cuotas == 0
    assert monto == 0.0


def test_reaplicar_mismo_corte_no_infla_cuotas_ni_monto():
    """
    Escenario: generar Impagas dos veces con el mismo fecha_hasta.

    Antes (bug): nuevo = sheet + impagas_periodo - cerradas → 5→6→7.
    Ahora: se escribe el corte BD; segunda pasada no cambia.
    """
    cort = {"cuotas_bd": 4.0, "monto_bd": 400.0}
    sheet_cuotas = 5
    sheet_monto = 500.0

    # Primera aplicación (hoja desfasada)
    nuevo1, monto1 = _valores_sync_desde_corte(cort)
    assert nuevo1 == 4
    assert monto1 == 400.0
    assert nuevo1 != sheet_cuotas
    assert abs(monto1 - sheet_monto) > 0.009

    # Segunda aplicación (hoja ya sincronizada)
    sheet_cuotas, sheet_monto = nuevo1, monto1
    nuevo2, monto2 = _valores_sync_desde_corte(cort)
    assert nuevo2 == sheet_cuotas == 4
    assert monto2 == sheet_monto == 400.0


def test_vieja_formula_delta_no_es_idempotente_documenta_bug():
    """Guarda el antitest: el delta sobre base de hoja sí se infla al repetir."""
    base = 5
    imp_p = 2
    cerr = 1
    run1 = max(0, base + imp_p - cerr)
    run2 = max(0, run1 + imp_p - cerr)
    assert run1 == 6
    assert run2 == 7  # corrupción que el corte absoluto evita


def test_monto_alineado_coincide_con_bd_si_cuotas_iguales():
    assert _monto_alineado(3, 3, 120.0) == 120.0
