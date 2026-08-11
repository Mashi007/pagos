"""Saldo residual unificado hoy/historico en desempeno cobranzas."""
from datetime import date

from app.services.cobranzas.universo_analisis_service import (
    _bucket_clave,
    _cuota_vencida_saldo_en_fecha,
)


def test_saldo_residual_igual_hoy_e_historico_con_abono_parcial():
    """Abono parcial: historico debe usar residual, no el monto completo."""
    monto = 100.0
    paid = 40.0
    fv = date(2026, 7, 1)
    dia = date(2026, 8, 9)
    hoy = date(2026, 8, 10)
    s_hist = _cuota_vencida_saldo_en_fecha(monto, paid, fv, None, dia, es_hoy=False)
    s_hoy = _cuota_vencida_saldo_en_fecha(monto, paid, fv, None, hoy, es_hoy=True)
    assert s_hist == 60.0
    assert s_hoy == 60.0


def test_excluye_pagado_sin_fecha_pago_tambien_en_historico():
    s = _cuota_vencida_saldo_en_fecha(
        100.0, 100.0, date(2026, 7, 1), None, date(2026, 8, 9), es_hoy=False
    )
    assert s is None


def test_excluye_si_fecha_pago_en_o_antes_del_dia():
    assert (
        _cuota_vencida_saldo_en_fecha(
            100.0, 0.0, date(2026, 7, 1), date(2026, 8, 9), date(2026, 8, 9)
        )
        is None
    )


def test_no_cuenta_sin_retraso():
    # Dia del vencimiento: atraso 0
    assert (
        _cuota_vencida_saldo_en_fecha(
            100.0, 0.0, date(2026, 8, 9), None, date(2026, 8, 9)
        )
        is None
    )


def test_bucket_excluyente():
    assert _bucket_clave(0) is None
    assert _bucket_clave(1) == "1"
    assert _bucket_clave(2) == "2"
    assert _bucket_clave(3) == "3"
    assert _bucket_clave(4) == "4plus"
    assert _bucket_clave(10) == "4plus"
