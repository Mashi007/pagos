# -*- coding: utf-8 -*-
"""Rescate pass 2 Gmail alineado con reglas Mercantil/BNC post-parse."""

from app.services.pagos_gmail.gemini_service import (
    PAGOS_NA,
    _gmail_fields_necesita_rescate_post_pass1,
    _gmail_merge_pass_results,
    _gmail_pass1_serial_mercantil_inaceptable,
    _gmail_puntaje_referencia_pass,
)


def test_necesita_rescate_serial_mercantil_14_digitos():
    needs, hint, reason = _gmail_fields_necesita_rescate_post_pass1(
        "A",
        {"numero_referencia": "74008740065053", "monto": "160", "fecha_pago": PAGOS_NA},
    )
    assert needs is True
    assert hint == "A"
    assert reason == "falto_ref"


def test_necesita_rescate_solo_dcme():
    needs, _, _ = _gmail_fields_necesita_rescate_post_pass1(
        "A",
        {
            "numero_referencia": "9264-20260618-115409-DCME-5574-A",
            "monto": "160",
        },
    )
    assert needs is True


def test_no_rescate_serial_15_ok():
    needs, _, _ = _gmail_fields_necesita_rescate_post_pass1(
        "A",
        {"numero_referencia": "740087459986093", "monto": "160"},
    )
    assert needs is False


def test_merge_prefiere_serial_15():
    f1 = {"numero_referencia": "74008740065053", "monto": "160", "fecha_pago": PAGOS_NA}
    f2 = {"numero_referencia": "740087459986093", "monto": "160", "fecha_pago": "18/06/2026"}
    fmt, merged = _gmail_merge_pass_results("A", f1, "A", f2)
    assert fmt == "A"
    assert merged["numero_referencia"] == "740087459986093"
    assert merged["fecha_pago"] == "18/06/2026"


def test_puntaje_serial_15_mayor_que_truncado():
    assert _gmail_puntaje_referencia_pass(
        {"numero_referencia": "740087459986093"}, "A"
    ) > _gmail_puntaje_referencia_pass(
        {"numero_referencia": "74008740065053"}, "A"
    )


def test_pass1_serial_inaceptable_dcme():
    assert _gmail_pass1_serial_mercantil_inaceptable(
        {"numero_referencia": "9264-20260618-115409-DCME-5574-A"}
    )
