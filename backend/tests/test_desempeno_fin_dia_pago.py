"""Fin dia baja cuando el prestamo sale del segmento el mismo dia."""
from datetime import date, datetime, time

from zoneinfo import ZoneInfo

from app.services.desempeno_1_cuota_stock import _paid_at_caracas, _stock_2_cuotas_at

Z = ZoneInfo("America/Caracas")
D = date(2026, 7, 13)
T0 = datetime.combine(D, time(0, 0, 0), tzinfo=Z)
T23 = datetime.combine(D, time(23, 0, 0), tzinfo=Z)


def test_fin_dia_baja_si_pago_con_hora_en_el_dia():
    meta = [
        {
            "prestamo_id": 100,
            "cliente_id": 1,
            "fv": date(2026, 4, 1),
            "paid_at": datetime.combine(D, time(12, 0, 0), tzinfo=Z),
        },
        {
            "prestamo_id": 100,
            "cliente_id": 1,
            "fv": date(2026, 5, 1),
            "paid_at": None,
        },
        {
            "prestamo_id": 200,
            "cliente_id": 2,
            "fv": date(2026, 4, 1),
            "paid_at": None,
        },
        {
            "prestamo_id": 200,
            "cliente_id": 2,
            "fv": date(2026, 5, 1),
            "paid_at": None,
        },
    ]
    s0 = _stock_2_cuotas_at(meta, T0, Z)
    sfin = _stock_2_cuotas_at(meta, T23, Z)
    assert s0 == {100, 200}
    assert (s0 & sfin) == {200}


def test_fecha_pago_solo_cuenta_antes_del_corte_23h():
    paid = _paid_at_caracas(fecha_pago=D, monto=100.0, eventos=[], z=Z)
    assert paid is not None
    assert T0 < paid <= T23
