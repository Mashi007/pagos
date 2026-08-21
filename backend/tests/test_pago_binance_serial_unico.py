"""Regla: serial Binance una sola vez en cartera (ignora §CD:)."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.core.documento import compose_numero_documento_almacenado
from app.services.pago_binance_serial_unico import (
    binance_tiene_codigo_o_validador,
    digitos_serial_binance,
    es_institucion_binance,
    mensaje_binance_rechaza_codigo,
    mensaje_conflicto_binance,
    primer_pago_id_mismo_serial_binance,
)


def test_digitos_ignoran_sufijo_cd():
    composed = compose_numero_documento_almacenado("419480309945163776", "A1020")
    assert "§CD:A1020" in (composed or "")
    assert digitos_serial_binance(composed) == "419480309945163776"
    assert digitos_serial_binance("419480309945163776") == "419480309945163776"


def test_es_institucion_binance():
    assert es_institucion_binance("Binance")
    assert es_institucion_binance("BINANCE Pay")
    assert not es_institucion_binance("BNC")
    assert not es_institucion_binance(None)


def test_binance_rechaza_codigo_validador():
    assert binance_tiene_codigo_o_validador(
        "419480309945163776", codigo_documento="A1020"
    )
    assert binance_tiene_codigo_o_validador(
        compose_numero_documento_almacenado("419480309945163776", "A1020")
    )
    assert not binance_tiene_codigo_o_validador("419480309945163776")
    assert "no se admite código" in mensaje_binance_rechaza_codigo().lower()


def test_primer_pago_bloquea_mismo_serial_con_codigo():
    """Caso 94243 vs 94245: mismo order id, segundo con §CD:A1020."""
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (94243, "419480309945163776", "Binance"),
    ]
    cid = primer_pago_id_mismo_serial_binance(
        db,
        compose_numero_documento_almacenado("419480309945163776", "A1020"),
        institucion_bancaria="BINANCE",
    )
    assert cid == 94243
    assert "94243" in mensaje_conflicto_binance(cid)


def test_sin_binance_ni_serial_largo_no_aplica():
    db = MagicMock()
    assert (
        primer_pago_id_mismo_serial_binance(
            db, "12345", institucion_bancaria="BNC"
        )
        is None
    )
    db.execute.assert_not_called()


def test_serial_binance_para_guardar_omite_codigo():
    from app.services.pago_binance_serial_unico import serial_binance_para_guardar

    composed = compose_numero_documento_almacenado("449869550776270848", "D1001")
    assert serial_binance_para_guardar(composed) == "449869550776270848"
    assert (
        serial_binance_para_guardar(
            "449869550776270848", codigo_documento="D1001"
        )
        == "449869550776270848"
    )


def test_mercantil_serial_largo_permite_codigo():
    """Mercantil 740087… (15 dígitos) no debe disparar regla Binance/§CD: bloqueado."""
    from app.services.pago_binance_serial_unico import debe_aplicar_unicidad_binance

    serial = "740087406774748"
    assert len(serial) >= 15
    assert not debe_aplicar_unicidad_binance(
        institucion_bancaria="Mercantil",
        numero_documento=serial,
    )
    assert binance_tiene_codigo_o_validador(serial, codigo_documento="D8396")
    # Con Binance sí aplica
    assert debe_aplicar_unicidad_binance(
        institucion_bancaria="BINANCE",
        numero_documento=serial,
    )


def test_ocr_resolver_binance_no_desambigua_con_codigo():
    """Sin desambiguar: si el base no es válido, debe fallar (no inventar §CD:)."""
    import app.services.revision_manual_conciliacion_cartera_service as mod

    orig_reg = mod.numero_documento_ya_registrado
    orig_h = mod.conflicto_huella_para_creacion
    try:
        mod.numero_documento_ya_registrado = lambda *_a, **_k: True
        mod.conflicto_huella_para_creacion = lambda *_a, **_k: None
        try:
            mod._resolver_numero_documento_conciliar_ocr(
                MagicMock(),
                num_op="447506042975010816",
                prestamo_id=1,
                reserva_orden=1,
                fecha_pago=date(2026, 8, 8),
                monto_pagado=Decimal("95"),
                permitir_desambiguar_codigo=False,
            )
            assert False, "debía fallar"
        except ValueError as e:
            assert "BINANCE" in str(e).upper() or "código" in str(e).lower()
    finally:
        mod.numero_documento_ya_registrado = orig_reg
        mod.conflicto_huella_para_creacion = orig_h
