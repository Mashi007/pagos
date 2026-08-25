# -*- coding: utf-8 -*-
"""Rescate Binance plantilla C en Gmail."""

import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pagos_gmail import binance_gmail_rescate as bg


def test_ya_control_ok_no_rescate():
    ctrl, rescate, motivo = bg.resolver_control_usuario_operaciones_gmail_plantilla_c(
        control_actual="true",
        monto_str="85",
        numero_referencia="740087401612580",
        cedula_columna="V12345678",
        fecha_pago_str="2026-03-10",
        image_bytes=b"fake",
    )
    assert ctrl == "true"
    assert rescate is False
    assert motivo == "ya_ok"


def test_sin_imagen_no_rescate():
    ctrl, rescate, motivo = bg.resolver_control_usuario_operaciones_gmail_plantilla_c(
        control_actual="false",
        monto_str="85",
        numero_referencia="740087401612580",
        cedula_columna="V12345678",
        fecha_pago_str="2026-03-10",
        image_bytes=None,
    )
    assert rescate is False
    assert motivo == "sin_imagen"


def test_rescate_compare_coincide():
    with patch(
        "app.services.pagos_gmail.gemini_service.compare_form_with_image",
        return_value={"coincide_exacto": True, "comentario": ""},
    ):
        ctrl, rescate, motivo = bg.resolver_control_usuario_operaciones_gmail_plantilla_c(
            control_actual="false",
            monto_str="85.00",
            numero_referencia="740087401612580",
            cedula_columna="V12345678",
            fecha_pago_str="2026-03-10",
            image_bytes=b"img",
            filename="binance.png",
        )
    assert ctrl == "true"
    assert rescate is True
    assert motivo == "compare_binance_digital"


def test_aplicar_rescate_pending_actualiza_control():
    row = {
        "fmt": "C",
        "control_usuario_operaciones": "false",
        "m": "85",
        "r": "740087401612580",
        "c": "V12345678",
        "f": "2026-03-10",
        "content": b"x",
        "filename": "c.png",
    }
    with patch(
        "app.services.pagos_gmail.gemini_service.compare_form_with_image",
        return_value={"coincide_exacto": True, "comentario": ""},
    ):
        out = bg.aplicar_rescate_binance_pending_gmail(dict(row))
    assert out["control_usuario_operaciones"] == "true"
    assert out.get("_binance_rescate") == "compare_binance_digital"
