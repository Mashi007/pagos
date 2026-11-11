# -*- coding: utf-8 -*-
"""Plan de cuotas debe sumar total_financiamiento aunque cuota_periodo esté desfasado."""
from types import SimpleNamespace

from app.api.v1.endpoints.prestamos.routes import _monto_cuota_tabla_desde_prestamo


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
