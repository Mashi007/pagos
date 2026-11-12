# -*- coding: utf-8 -*-
"""Plan de cuotas debe sumar total_financiamiento aunque cuota_periodo esté desfasado."""
from types import SimpleNamespace

from decimal import Decimal

from app.api.v1.endpoints.prestamos.routes import (
    _monto_cuota_tabla_desde_prestamo,
    _montos_plan_plano,
)


def _p(cuota_periodo, tasa=0):
    return SimpleNamespace(
        id=3625, tasa_interes=tasa, cuota_periodo=cuota_periodo, modalidad_pago="MENSUAL"
    )


def test_cuota_periodo_desfasado_usa_cuota_plana():
    assert _monto_cuota_tabla_desde_prestamo(_p(140), 1704.0, 12) == 142.0


def test_cuota_periodo_coherente_se_respeta():
    assert _monto_cuota_tabla_desde_prestamo(_p(142), 1704.0, 12) == 142


def test_cuota_periodo_con_redondeo_se_respeta():
    assert _monto_cuota_tabla_desde_prestamo(_p(333.33), 1000.0, 3) == 333.33


def test_sin_cuota_periodo_usa_cuota_plana():
    assert _monto_cuota_tabla_desde_prestamo(_p(0), 1680.0, 12) == 140.0


def test_total_no_divisible_la_ultima_cuota_absorbe_el_residuo():
    """12× round(1705/12, 2) = 1704.96, por encima de la tolerancia de cuadre 0.02."""
    igual = Decimal(str(round(1705 / 12, 2)))
    assert igual * 12 == Decimal("1704.96")
    assert abs(igual * 12 - Decimal("1705.00")) > Decimal("0.02")

    montos = _montos_plan_plano(1705 / 12, 12, 1705.0)
    assert montos[:-1] == [Decimal("142.08")] * 11
    assert montos[-1] == Decimal("142.12")
    assert sum(montos) == Decimal("1705.00")


def test_cuota_redondeada_dentro_de_tolerancia_igual_cuadra_el_total():
    """83.33×12 = 999.96 cabe en 1 centavo por cuota, pero no en el cuadre de 0.02."""
    assert _monto_cuota_tabla_desde_prestamo(_p(83.33), 1000.0, 12) == 83.33
    montos = _montos_plan_plano(83.33, 12, 1000.0)
    assert montos[:-1] == [Decimal("83.33")] * 11
    assert montos[-1] == Decimal("83.37")
    assert sum(montos) == Decimal("1000.00")


def test_plan_exacto_no_altera_la_ultima_cuota():
    montos = _montos_plan_plano(142.0, 12, 1704.0)
    assert montos == [Decimal("142.00")] * 12
    assert sum(montos) == Decimal("1704.00")


def test_cuota_333_33_la_ultima_cierra_el_centavo():
    assert _monto_cuota_tabla_desde_prestamo(_p(333.33), 1000.0, 3) == 333.33
    montos = _montos_plan_plano(333.33, 3, 1000.0)
    assert montos == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert sum(montos) == Decimal("1000.00")


def test_sin_total_objetivo_mantiene_cuotas_iguales():
    montos = _montos_plan_plano(1000 / 12, 12, None)
    assert montos == [Decimal("83.33")] * 12


def test_residuo_no_deja_cuota_final_en_cero():
    montos = _montos_plan_plano(0.02 / 3, 3, 0.02)
    assert all(m >= 0 for m in montos)
    assert sum(montos) == Decimal("0.02")
    assert montos[-1] > 0
