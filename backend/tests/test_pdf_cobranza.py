# -*- coding: utf-8 -*-
"""
Tests del servicio de generación de PDF de carta de cobranza.
Prioridad: validar que el módulo genera bytes PDF con contexto mínimo y que sanitización no rompe.

Ejecutar desde backend/:
  pytest tests/test_pdf_cobranza.py -v
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.carta_cobranza_pdf import (
    _sanitize_for_reportlab,
    _format_fecha,
    _datos_desde_contexto,
    generar_carta_cobranza_pdf,
)


# --- Sanitización y formato ---

def test_sanitize_for_reportlab_empty():
    """_sanitize_for_reportlab con None o vacío devuelve cadena vacía."""
    assert _sanitize_for_reportlab(None) == ""
    assert _sanitize_for_reportlab("") == ""


def test_sanitize_for_reportlab_removes_emoji():
    """_sanitize_for_reportlab reemplaza emojis por espacio."""
    t = "Hola \u2709 mundo"
    assert "\u2709" not in _sanitize_for_reportlab(t)
    assert "Hola" in _sanitize_for_reportlab(t) and "mundo" in _sanitize_for_reportlab(t)


def test_format_fecha_date():
    """_format_fecha con date devuelve dd/mm/yyyy."""
    from datetime import date
    assert _format_fecha(date(2025, 3, 13)) == "13/03/2025"


def test_format_fecha_iso_string():
    """_format_fecha con string ISO devuelve dd/mm/yyyy."""
    assert _format_fecha("2025-03-13") == "13/03/2025"


def test_datos_desde_contexto_empty():
    """_datos_desde_contexto con contexto vacío devuelve dict con claves esperadas."""
    out = _datos_desde_contexto({})
    assert isinstance(out, dict)
    assert "fecha_carta" in out
    assert "nombre_completo" in out
    assert "monto_total_usd" in out
    assert out["monto_total_usd"] == "0.00"


def test_datos_desde_contexto_with_cuotas():
    """_datos_desde_contexto con cuotas formatea fechas y montos."""
    ctx = {
        "FECHA_CARTA": "2025-03-13",
        "CUOTAS.VENCIMIENTOS": [
            {"fecha_vencimiento": "2025-02-01", "monto": 100},
            {"fecha_vencimiento": "2025-03-01", "monto_cuota": 150},
        ],
    }
    out = _datos_desde_contexto(ctx)
    assert isinstance(out, dict)


# --- Generación PDF (integración mínima) ---

def test_generar_carta_cobranza_pdf_returns_bytes():
    """generar_carta_cobranza_pdf con contexto mínimo devuelve bytes (PDF)."""
    contexto = {
        "CLIENTES.NOMBRE": "Juan",
        "CLIENTES.APELLIDO": "Pérez",
        "FECHA_CARTA": "2025-03-13",
        "CUOTAS.VENCIMIENTOS": [],
    }
    pdf_bytes = generar_carta_cobranza_pdf(contexto, db=None)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 200
