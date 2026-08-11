"""Saldo as-of: cobros de hoy no reescriben ayer (se ve la mejora)."""
from datetime import date

from app.services.cobranzas.universo_analisis_service import (
    _bucket_clave,
    _cuota_vencida_saldo_en_fecha,
    _pagado_al_dia,
)


def test_cobro_hoy_baja_hoy_pero_no_ayer():
    """Pago aplicado hoy: ayer sigue con deuda; hoy residual 0 → mejora visible."""
    monto = 100.0
    fv = date(2026, 7, 1)
    ayer = date(2026, 8, 9)
    hoy = date(2026, 8, 10)
    eventos = [(hoy, 100.0)]  # cobro hoy
    pag_ayer = _pagado_al_dia(
        monto=monto,
        fecha_pago=hoy,
        eventos=eventos,
        dia=ayer,
        total_pagado_actual=100.0,
        es_hoy=False,
    )
    pag_hoy = _pagado_al_dia(
        monto=monto,
        fecha_pago=hoy,
        eventos=eventos,
        dia=hoy,
        total_pagado_actual=100.0,
        es_hoy=True,
    )
    s_ayer = _cuota_vencida_saldo_en_fecha(monto, fv, hoy, ayer, pag_ayer)
    s_hoy = _cuota_vencida_saldo_en_fecha(monto, fv, hoy, hoy, pag_hoy)
    assert s_ayer == 100.0
    assert s_hoy is None


def test_abono_parcial_as_of_reduce_desde_ese_dia():
    monto = 100.0
    fv = date(2026, 7, 1)
    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 5)
    eventos = [(d1, 40.0)]
    p1 = _pagado_al_dia(
        monto=monto, fecha_pago=None, eventos=eventos, dia=d1,
        total_pagado_actual=40.0, es_hoy=False,
    )
    p0 = _pagado_al_dia(
        monto=monto, fecha_pago=None, eventos=eventos, dia=date(2026, 7, 20),
        total_pagado_actual=40.0, es_hoy=False,
    )
    assert _cuota_vencida_saldo_en_fecha(monto, fv, None, date(2026, 7, 20), p0) == 100.0
    assert _cuota_vencida_saldo_en_fecha(monto, fv, None, d1, p1) == 60.0
    assert _cuota_vencida_saldo_en_fecha(monto, fv, None, d2, p1) == 60.0


def test_hoy_usa_total_pagado_si_eventos_atrasados():
    monto = 100.0
    hoy = date(2026, 8, 10)
    pag = _pagado_al_dia(
        monto=monto,
        fecha_pago=None,
        eventos=[],
        dia=hoy,
        total_pagado_actual=100.0,
        es_hoy=True,
    )
    assert _cuota_vencida_saldo_en_fecha(monto, date(2026, 7, 1), None, hoy, pag) is None


def test_historico_sin_eventos_no_usa_total_pagado_actual():
    """Sin cuota_pagos, un cobro solo en total_pagado no reescribe el pasado."""
    monto = 100.0
    ayer = date(2026, 8, 9)
    pag = _pagado_al_dia(
        monto=monto,
        fecha_pago=None,
        eventos=[],
        dia=ayer,
        total_pagado_actual=100.0,
        es_hoy=False,
    )
    assert pag == 0.0
    assert _cuota_vencida_saldo_en_fecha(monto, date(2026, 7, 1), None, ayer, pag) == 100.0


def test_excluye_si_fecha_pago_en_o_antes_del_dia():
    pag = _pagado_al_dia(
        monto=100.0,
        fecha_pago=date(2026, 8, 9),
        eventos=[],
        dia=date(2026, 8, 9),
        total_pagado_actual=0.0,
        es_hoy=False,
    )
    assert (
        _cuota_vencida_saldo_en_fecha(
            100.0, date(2026, 7, 1), date(2026, 8, 9), date(2026, 8, 9), pag
        )
        is None
    )


def test_no_cuenta_sin_retraso():
    assert (
        _cuota_vencida_saldo_en_fecha(
            100.0, date(2026, 8, 9), None, date(2026, 8, 9), 0.0
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
