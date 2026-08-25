# -*- coding: utf-8 -*-
"""Rescate determinístico post-Gemini (Cobros auto-aprobación)."""

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cobros.comprobante_coincidencia_rescate import (
    evaluar_rescate_coincidencia_determinista,
    montos_coinciden_determinista,
    seriales_coinciden_determinista,
)


def _form(**kw):
    base = {
        "fecha_pago": "2026-03-10",
        "institucion_financiera": "BNC",
        "numero_operacion": "740087401612580",
        "monto": "85.00",
        "moneda": "USD",
        "tipo_cedula": "V",
        "numero_cedula": "12345678",
    }
    base.update(kw)
    return base


def test_no_rescate_si_ya_coincide():
    ok, _ = evaluar_rescate_coincidencia_determinista(
        _form(), coincide=True, comentario="", extraccion={}, control_usuario_operaciones=None
    )
    assert ok is False


def test_no_rescate_ocr_borroso():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(),
        coincide=False,
        comentario="Serial borroso, Nº operación",
        extraccion={"monto": "85", "numero_operacion": "740087401612580"},
        control_usuario_operaciones=None,
    )
    assert ok is False
    assert motivo == "ocr_borroso"


def test_no_rescate_binance_sin_control_operaciones():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(institucion_financiera="BINANCE", moneda="USDT"),
        coincide=False,
        comentario="Fecha pago, Cédula",
        extraccion={
            "monto": "85",
            "numero_operacion": "740087401612580",
            "moneda": "USDT",
        },
        control_usuario_operaciones=False,
    )
    assert ok is False
    assert motivo == "binance_sin_control"


def test_rescate_binance_digital_control_ok():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(institucion_financiera="BINANCE", moneda="USDT"),
        coincide=False,
        comentario="Fecha pago, Cédula, Banco",
        extraccion={
            "monto": "85.00 USDT",
            "numero_operacion": "740087401612580",
            "moneda": "USDT",
        },
        control_usuario_operaciones=True,
    )
    assert ok is True
    assert motivo == "binance_digital"


def test_no_rescate_usuario_operaciones():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(institucion_financiera="BINANCE"),
        coincide=False,
        comentario="Usuario operaciones",
        extraccion={"monto": "85", "numero_operacion": "740087401612580"},
        control_usuario_operaciones=False,
    )
    assert ok is False
    assert motivo == "binance_control_operaciones"


def test_rescate_general_falso_negativo_banco():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(institucion_financiera="Mercantil"),
        coincide=False,
        comentario="Banco",
        extraccion={
            "monto": "85",
            "numero_operacion": "740087401612580",
            "institucion_financiera": "Banco Mercantil",
        },
        control_usuario_operaciones=None,
    )
    assert ok is True
    assert motivo == "deterministico"


def test_no_rescate_monto_distinto():
    ok, motivo = evaluar_rescate_coincidencia_determinista(
        _form(monto="85"),
        coincide=False,
        comentario="Monto",
        extraccion={"monto": "120", "numero_operacion": "740087401612580"},
        control_usuario_operaciones=None,
    )
    assert ok is False
    assert motivo == "criticos_no_verificables"


def test_montos_usdt_usd_equivalentes():
    assert montos_coinciden_determinista("85", "85.00 USDT", moneda_form="USD", moneda_ext="USDT")


def test_seriales_canonico_iguales():
    assert seriales_coinciden_determinista(
        "740087401612580",
        "740087401612580",
        institucion="BNC",
    )
