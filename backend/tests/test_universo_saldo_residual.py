"""Segmentacion cobranzas: ventanas 1-30 / 6-60 / 6-90 / 6-120 / 6-150 / 6+."""
from datetime import date

from app.services.cobranzas.universo_analisis_service import (
    _aplicar_exclusion_cliente_bucket_1,
    _bucket_clave,
    _bucket_clave_desde_atrasos,
    _cuota_vencida_saldo_en_fecha,
    _pagado_al_dia,
)


def test_1_cuota_atraso_1_a_30():
    assert _bucket_clave_desde_atrasos([0]) is None
    assert _bucket_clave_desde_atrasos([1]) == "1"
    assert _bucket_clave_desde_atrasos([5]) == "1"
    assert _bucket_clave_desde_atrasos([6]) == "1"
    assert _bucket_clave_desde_atrasos([30]) == "1"
    assert _bucket_clave_desde_atrasos([31]) is None


def test_2_3_ventanas_y_4_5_6plus():
    assert _bucket_clave_desde_atrasos([10, 20]) == "2"
    assert _bucket_clave_desde_atrasos([10, 70]) is None  # max>60
    assert _bucket_clave_desde_atrasos([10, 20, 30]) == "3"
    assert _bucket_clave_desde_atrasos([10, 20, 100]) is None  # max>90
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40]) == "4"
    assert _bucket_clave_desde_atrasos([10, 20, 30, 130]) is None  # max>120
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 50]) == "5"
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 160]) is None  # max>150
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 50, 60]) == "6plus"
    # 2 cuotas con una <6: no entra a bucket 2 ni se disfraza de 1
    assert _bucket_clave_desde_atrasos([3, 10]) is None


def test_exclusion_cliente_quita_1_cuota():
    filas = [
        (100, 7, "1", 50.0),
        (200, 7, "2", 80.0),
        (300, 8, "1", 40.0),
    ]
    out = _aplicar_exclusion_cliente_bucket_1(filas)
    pids = {r[0] for r in out}
    assert 100 not in pids
    assert 200 in pids
    assert 300 in pids


def test_cobro_hoy_baja_hoy_pero_no_ayer():
    monto = 100.0
    fv = date(2026, 7, 1)
    ayer = date(2026, 8, 9)
    hoy = date(2026, 8, 10)
    eventos = [(hoy, 100.0)]
    pag_ayer = _pagado_al_dia(
        monto=monto, fecha_pago=hoy, eventos=eventos, dia=ayer,
        total_pagado_actual=100.0, es_hoy=False,
    )
    pag_hoy = _pagado_al_dia(
        monto=monto, fecha_pago=hoy, eventos=eventos, dia=hoy,
        total_pagado_actual=100.0, es_hoy=True,
    )
    assert _cuota_vencida_saldo_en_fecha(monto, fv, hoy, ayer, pag_ayer) == 100.0
    assert _cuota_vencida_saldo_en_fecha(monto, fv, hoy, hoy, pag_hoy) is None


def test_bucket_clave_compat():
    assert _bucket_clave(0) is None
    assert _bucket_clave(1) == "1"
    assert _bucket_clave(4) == "4"
    assert _bucket_clave(5) == "5"
    assert _bucket_clave(6) == "6plus"
