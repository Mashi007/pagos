"""Filtro 3 dias antes: solo si la cuota anterior fue impuntual."""
from datetime import date
from types import SimpleNamespace

from app.services.notificacion_service import (
    cuota_fue_impuntual,
    prestamo_califica_aviso_3_dias_antes_por_impuntualidad,
    ultima_cuota_anterior_mismo_prestamo,
)

HOY = date(2026, 7, 24)


def _c(**kw):
    return SimpleNamespace(**kw)


def test_impuntual_pago_tarde():
    c = _c(fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 6, 5))
    assert cuota_fue_impuntual(c, HOY) is True


def test_puntual_pago_mismo_dia():
    c = _c(fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 6, 1))
    assert cuota_fue_impuntual(c, HOY) is False


def test_puntual_pago_antes():
    c = _c(fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 5, 28))
    assert cuota_fue_impuntual(c, HOY) is False


def test_impuntual_sigue_vencida_sin_pago():
    c = _c(fecha_vencimiento=date(2026, 7, 1), fecha_pago=None)
    assert cuota_fue_impuntual(c, HOY) is True


def test_no_impuntual_si_aun_no_vence():
    c = _c(fecha_vencimiento=date(2026, 8, 1), fecha_pago=None)
    assert cuota_fue_impuntual(c, HOY) is False


def test_ultima_anterior_por_numero():
    c1 = _c(id=1, numero_cuota=1, fecha_vencimiento=date(2026, 5, 1), fecha_pago=date(2026, 5, 1))
    c2 = _c(id=2, numero_cuota=2, fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 6, 10))
    c3 = _c(id=3, numero_cuota=3, fecha_vencimiento=date(2026, 7, 27), fecha_pago=None)
    assert ultima_cuota_anterior_mismo_prestamo([c1, c2, c3], c3) is c2


def test_califica_si_anterior_impuntual():
    prev = _c(id=1, numero_cuota=1, fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 6, 8))
    prox = _c(id=2, numero_cuota=2, fecha_vencimiento=date(2026, 7, 27), fecha_pago=None)
    assert prestamo_califica_aviso_3_dias_antes_por_impuntualidad([prev, prox], prox, HOY) is True


def test_no_califica_si_anterior_puntual():
    prev = _c(id=1, numero_cuota=1, fecha_vencimiento=date(2026, 6, 1), fecha_pago=date(2026, 6, 1))
    prox = _c(id=2, numero_cuota=2, fecha_vencimiento=date(2026, 7, 27), fecha_pago=None)
    assert prestamo_califica_aviso_3_dias_antes_por_impuntualidad([prev, prox], prox, HOY) is False


def test_no_califica_sin_cuota_anterior():
    prox = _c(id=1, numero_cuota=1, fecha_vencimiento=date(2026, 7, 27), fecha_pago=None)
    assert prestamo_califica_aviso_3_dias_antes_por_impuntualidad([prox], prox, HOY) is False
