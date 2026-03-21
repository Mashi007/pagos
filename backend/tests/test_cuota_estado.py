"""Tests unitarios de clasificacion y etiquetas de estado de cuota (sin BD)."""
from datetime import date


from app.services.cuota_estado import (
    clasificar_estado_cuota,
    etiqueta_estado_cuota,
    dias_retraso_desde_vencimiento,
)


def test_pagado_mismo_dia_vencimiento():
    ref = date(2025, 6, 15)
    fv = date(2025, 6, 15)
    assert clasificar_estado_cuota(100.0, 100.0, fv, ref) == "PAGADO"


def test_pago_adelantado():
    ref = date(2025, 6, 10)
    fv = date(2025, 6, 20)
    assert clasificar_estado_cuota(50.0, 50.0, fv, ref) == "PAGO_ADELANTADO"


def test_pendiente_sin_abono():
    ref = date(2025, 6, 10)
    fv = date(2025, 6, 15)
    assert clasificar_estado_cuota(0.0, 100.0, fv, ref) == "PENDIENTE"


def test_parcial_sin_retraso():
    ref = date(2025, 6, 10)
    fv = date(2025, 6, 15)
    assert clasificar_estado_cuota(30.0, 100.0, fv, ref) == "PARCIAL"


def test_vencido_91_dias():
    ref = date(2025, 9, 14)
    fv = date(2025, 6, 15)
    assert dias_retraso_desde_vencimiento(fv, ref) == 91
    assert clasificar_estado_cuota(0.0, 100.0, fv, ref) == "VENCIDO"


def test_mora_desde_dia_92():
    ref = date(2025, 9, 15)
    fv = date(2025, 6, 15)
    assert dias_retraso_desde_vencimiento(fv, ref) == 92
    assert clasificar_estado_cuota(0.0, 100.0, fv, ref) == "MORA"


def test_tolerancia_monto_casi_completo():
    ref = date(2025, 6, 15)
    fv = date(2025, 6, 10)
    assert clasificar_estado_cuota(99.995, 100.0, fv, ref) == "PAGADO"


def test_etiquetas_paridad_frontend():
    assert etiqueta_estado_cuota("PENDIENTE") == "Pendiente"
    assert etiqueta_estado_cuota("PARCIAL") == "Pendiente parcial"
    assert etiqueta_estado_cuota("VENCIDO") == "Vencido"
    assert etiqueta_estado_cuota("MORA") == "Mora (92+ d)"
    assert etiqueta_estado_cuota("PAGADO") == "Pagado"
    assert etiqueta_estado_cuota("PAGO_ADELANTADO") == "Pago adelantado"
    assert etiqueta_estado_cuota("PAGADA") == "Pagado"
