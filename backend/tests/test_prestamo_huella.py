"""Tests de normalizacion huella duplicados (prestamo_huella)."""
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.prestamos.prestamo_huella import (
    ensure_no_duplicate_aprobado_huella,
    normalizar_cedula_huella,
    normalizar_modalidad_producto,
)


def test_normalizar_cedula_huella_trim():
    assert normalizar_cedula_huella("  v123  ") == "V123"


def test_normalizar_modalidad_producto_vacio():
    assert normalizar_modalidad_producto(None) == ""
    assert normalizar_modalidad_producto("  mensual  ") == "MENSUAL"


def test_j_permite_misma_huella_aprobado(monkeypatch):
    """J410091410 y demás J pueden tener n APROBADO aunque la huella coincida."""
    p = MagicMock()
    p.estado = "APROBADO"
    p.cedula = "J410091410"
    p.id = None
    p.fecha_requerimiento = date(2026, 3, 27)
    p.total_financiamiento = Decimal("3000")
    p.numero_cuotas = 15
    p.cuota_periodo = Decimal("200")
    p.tasa_interes = Decimal("0")
    p.modalidad_pago = "MENSUAL"
    p.producto = "X"

    def _boom(*_a, **_k):
        raise AssertionError("no debe consultar huella para J")

    monkeypatch.setattr(
        "app.services.prestamos.prestamo_huella.contar_otros_aprobados_misma_huella",
        _boom,
    )
    ensure_no_duplicate_aprobado_huella(MagicMock(), p)


def test_v_sigue_bloqueando_misma_huella(monkeypatch):
    p = MagicMock()
    p.estado = "APROBADO"
    p.cedula = "V16874928"
    p.id = None
    p.fecha_requerimiento = date(2026, 8, 1)
    p.total_financiamiento = Decimal("1000")
    p.numero_cuotas = 12
    p.cuota_periodo = Decimal("100")
    p.tasa_interes = Decimal("0")
    p.modalidad_pago = "MENSUAL"
    p.producto = "X"

    monkeypatch.setattr(
        "app.services.prestamos.prestamo_huella.contar_otros_aprobados_misma_huella",
        lambda *a, **k: 1,
    )
    with pytest.raises(HTTPException) as exc:
        ensure_no_duplicate_aprobado_huella(MagicMock(), p)
    assert exc.value.status_code == 409
