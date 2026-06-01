"""Parsers compartidos de monto/fecha (escáner Infopagos y Gmail)."""
from datetime import date

from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail, normalizar_fecha_pago
from app.services.pagos_gmail.parse_campos_comprobante import (
    normalizar_campos_gemini_gmail,
    parse_fecha_comprobante,
    parse_monto_comprobante,
)

REF = date(2026, 5, 31)


def test_parse_monto_comprobante_miles_venezolanos():
    assert parse_monto_comprobante("1.500,00") == 1500.0
    assert parse_monto_comprobante("1.500") == 1500.0
    assert parse_monto_comprobante("15.000,50") == 15000.5
    assert parse_monto_comprobante("150,50") == 150.5
    assert parse_monto_comprobante("150.25") == 150.25


def test_parse_monto_comprobante_mercantil_asteriscos_y_ocr():
    assert parse_monto_comprobante("***********96,00 USD") == 96.0
    assert parse_monto_comprobante("***********98,00 USD") == 98.0
    assert parse_monto_comprobante("969") == 96.0
    assert parse_monto_comprobante("965") == 96.0
    assert parse_monto_comprobante("980") == 98.0
    assert parse_monto_comprobante("150") == 150.0


def test_parse_fecha_comprobante():
    assert parse_fecha_comprobante("31/05/2026", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("31/05/26", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("2026-05-31", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante(
        "fecha operacion 21/04/2025 sello", REF
    ) == date(2025, 4, 21)
    assert parse_fecha_comprobante("310526", REF) == date(2026, 5, 31)
    assert parse_fecha_comprobante("09-02-2025", REF) == date(2025, 2, 9)
    assert parse_fecha_comprobante(
        "9824-20250703-151620-DCME-4279-A", REF
    ) == date(2025, 7, 3)
    assert parse_fecha_comprobante("2027-01-01", REF) is None
    assert parse_fecha_comprobante("", REF) is None


def test_format_monto_excel_pagos_gmail_miles():
    assert format_monto_excel_pagos_gmail("1.500") == "1500.00"
    assert format_monto_excel_pagos_gmail("Bs. 15.000,50") == "15000.50"
    assert format_monto_excel_pagos_gmail("NR") == "NR"


def test_normalizar_fecha_pago_valida():
    assert normalizar_fecha_pago("31/05/2026", ref_hoy=REF) == "31/05/2026"


def test_normalizar_campos_gemini_gmail_fecha_futura():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "2027-01-01",
            "monto": "10.00",
            "cedula": "NA",
            "numero_referencia": "123",
        }
    )
    assert out["fecha_pago"] == "NA"
    assert out["monto"] == "10.00"


def test_normalizar_campos_gemini_gmail():
    out = normalizar_campos_gemini_gmail(
        {
            "fecha_pago": "31/05/2026",
            "monto": "1.500",
            "cedula": "NA",
            "numero_referencia": "123",
        }
    )
    assert out["monto"] == "1500.00"
    assert out["fecha_pago"] == "31/05/2026"
