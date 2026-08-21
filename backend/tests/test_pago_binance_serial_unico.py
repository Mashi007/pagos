"""Regla: serial Binance una sola vez en cartera (ignora §CD:)."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.core.documento import compose_numero_documento_almacenado
from app.services.pago_binance_serial_unico import (
    digitos_serial_binance,
    es_institucion_binance,
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


def test_primer_pago_bloquea_mismo_serial_con_codigo():
    """Caso 94243 vs 94245: mismo order id, segundo con §CD:A1020."""
    db = MagicMock()
    # Primera consulta LIKE: devuelve el pago original sin código
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
