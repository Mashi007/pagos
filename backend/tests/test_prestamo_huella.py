"""Tests de normalizacion huella duplicados (prestamo_huella)."""
from app.services.prestamos.prestamo_huella import (
    normalizar_cedula_huella,
    normalizar_modalidad_producto,
)


def test_normalizar_cedula_huella_trim():
    assert normalizar_cedula_huella("  v123  ") == "V123"


def test_normalizar_modalidad_producto_vacio():
    assert normalizar_modalidad_producto(None) == ""
    assert normalizar_modalidad_producto("  mensual  ") == "MENSUAL"
