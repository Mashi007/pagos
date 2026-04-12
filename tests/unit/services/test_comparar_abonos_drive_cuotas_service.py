"""
Tests unitarios para huella hoja vs préstamo (ABONOS / notificaciones).

Requiere las mismas variables de entorno que el backend al importar `app`
(p. ej. DATABASE_URL, SECRET_KEY) y PYTHONPATH=backend, como el resto de pytest del repo.
"""

from types import SimpleNamespace

import pytest

from app.services.comparar_abonos_drive_cuotas_service import (
    UMBRAL_CONFIRMO_ABONOS_USD,
    _fila_hoja_coincide_prestamo,
    _parse_monto_celda_hoja,
)


@pytest.mark.unit
def test_fila_hoja_coincide_prestamo_cuando_alinea():
    prestamo = SimpleNamespace(
        total_financiamiento=10000,
        numero_cuotas=12,
        modalidad_pago="SEMANAL",
    )
    cells = {"TF": 10000, "NC": 12, "MOD": "SEMANAL"}
    assert _fila_hoja_coincide_prestamo(cells, prestamo, "TF", "MOD", "NC") is True


@pytest.mark.unit
def test_fila_hoja_no_coincide_financiamiento():
    prestamo = SimpleNamespace(
        total_financiamiento=10000,
        numero_cuotas=12,
        modalidad_pago="SEMANAL",
    )
    cells = {"TF": 9990, "NC": 12, "MOD": "SEMANAL"}
    assert _fila_hoja_coincide_prestamo(cells, prestamo, "TF", "MOD", "NC") is False


@pytest.mark.unit
def test_fila_hoja_no_coincide_modalidad():
    prestamo = SimpleNamespace(
        total_financiamiento=5000,
        numero_cuotas=6,
        modalidad_pago="MENSUAL",
    )
    cells = {"TF": 5000, "NC": 6, "MOD": "SEMANAL"}
    assert _fila_hoja_coincide_prestamo(cells, prestamo, "TF", "MOD", "NC") is False


@pytest.mark.unit
def test_parse_monto_celda_hoja_con_miles_y_decimales():
    assert _parse_monto_celda_hoja("1.234,56") == pytest.approx(1234.56)
    assert _parse_monto_celda_hoja("Bs 100") == pytest.approx(100.0)


@pytest.mark.unit
def test_umbral_confirma_exportado():
    assert UMBRAL_CONFIRMO_ABONOS_USD == 5000.0
