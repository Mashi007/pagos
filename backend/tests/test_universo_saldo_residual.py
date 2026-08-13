"""Segmentacion cobranzas: solo por cantidad de cuotas atrasadas (sin tope de dias)."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.cobranzas.universo_analisis_service import (
    _aplicar_exclusion_cliente_bucket_1,
    _bucket_clave_desde_atrasos,
    _cuota_vencida_saldo_en_fecha,
    _pagado_al_dia,
    _stock_resto6plus_at,
)
from app.services.desempeno_1_cuota_stock import (
    _cumple_ventana_segmento,
    _stock_6plus_cuotas_at,
    _stock_exact_n_cuotas_at,
)


def test_segmento_solo_por_conteo():
    assert _bucket_clave_desde_atrasos([]) is None
    assert _bucket_clave_desde_atrasos([1]) == "1"
    assert _bucket_clave_desde_atrasos([31]) == "1"  # dias no importan
    assert _bucket_clave_desde_atrasos([10, 200]) == "2"
    assert _bucket_clave_desde_atrasos([10, 20, 100]) == "3"
    assert _bucket_clave_desde_atrasos([10, 20, 30, 130]) == "4"
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 160]) == "5"
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 50, 200]) == "6plus"
    assert _bucket_clave_desde_atrasos([3, 10]) == "2"  # dia 3 tambien cuenta


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


def test_exact_6_sin_tope_dias():
    assert _cumple_ventana_segmento([10, 20, 30, 40, 50, 200], 6) is True
    assert _bucket_clave_desde_atrasos([10, 20, 30, 40, 50, 200]) == "6plus"


def test_prestamo_6_atrasadas_va_a_segmento_6_sin_mirar_dias():
    """Caso V13643497 / prestamo 7: 6 mora aunque >100 dias → segmento 6."""
    Z = ZoneInfo("America/Caracas")
    HOY = date(2026, 8, 12)
    T = datetime.combine(HOY, time(12, 0, 0), tzinfo=Z)

    def _c(pid, fv):
        return {"prestamo_id": pid, "cliente_id": 1, "fv": fv, "paid_at": None}

    meta = [_c(7, HOY - timedelta(days=d)) for d in (509, 478, 448, 417, 387, 356)]
    assert _stock_exact_n_cuotas_at(meta, T, Z, 6) == {7}
    assert _stock_resto6plus_at(meta, T, Z) == set()


def test_resto6plus_es_16_o_mas():
    Z = ZoneInfo("America/Caracas")
    HOY = date(2026, 7, 24)
    T0 = datetime.combine(HOY, time(0, 0, 0), tzinfo=Z)

    def _c(pid, cid, fv):
        return {"prestamo_id": pid, "cliente_id": cid, "fv": fv, "paid_at": None}

    meta_6 = [
        _c(1, 7, date(2026, 1, 1)),
        _c(1, 7, date(2026, 2, 1)),
        _c(1, 7, date(2026, 3, 1)),
        _c(1, 7, date(2026, 4, 1)),
        _c(1, 7, date(2026, 5, 1)),
        _c(1, 7, date(2026, 6, 1)),
    ]
    meta_16 = [_c(2, 8, HOY - timedelta(days=i + 1)) for i in range(16)]
    meta = meta_6 + meta_16
    assert _stock_exact_n_cuotas_at(meta, T0, Z, 6) == {1}
    assert _stock_6plus_cuotas_at(meta, T0, Z) == {1, 2}
    assert _stock_resto6plus_at(meta, T0, Z) == {2}


def test_comparativo_dia_1_meses_recorre():
    from app.services.cobranzas.universo_analisis_service import (
        _etiqueta_lectura,
        _fechas_3_meses_ayer_hoy,
    )

    hoy = date(2026, 8, 12)
    fechas = _fechas_3_meses_ayer_hoy(hoy)
    assert fechas == [
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 8, 11),
        date(2026, 8, 12),
    ]
    assert _etiqueta_lectura(fechas[0], hoy) == "1 de junio"
    assert _etiqueta_lectura(fechas[1], hoy) == "1 de julio"
    assert _etiqueta_lectura(fechas[2], hoy) == "1 de agosto"
    assert _etiqueta_lectura(fechas[3], hoy) == "Ayer 11/08"
    assert _etiqueta_lectura(fechas[4], hoy) == "Hoy 12/08"

    # Si hoy es el 1, no duplicar: usa 3 meses anteriores + ayer + hoy
    hoy_1 = date(2026, 9, 1)
    fechas_1 = _fechas_3_meses_ayer_hoy(hoy_1)
    assert fechas_1 == [
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 8, 31),
        date(2026, 9, 1),
    ]

