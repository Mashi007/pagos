"""Aviso: recibo ya en cola Cobros no debe duplicarse."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.cobros.pago_reportado_documento import (
    MSG_PAGO_EN_PROCESO_ADMIN,
    mensaje_pago_en_proceso_admin,
    primer_reportado_en_proceso_mismo_serial,
)


def test_mensaje_pago_en_proceso_incluye_referencia():
    assert "no se procesa" in MSG_PAGO_EN_PROCESO_ADMIN.lower()
    assert "administrador" in MSG_PAGO_EN_PROCESO_ADMIN.lower()
    assert "no puede duplicarse" in MSG_PAGO_EN_PROCESO_ADMIN.lower()
    msg = mensaje_pago_en_proceso_admin("RPC-20260821-00001")
    assert "RPC-20260821-00001" in msg
    assert "cola" in msg.lower() or "referencia" in msg.lower()


def test_primer_reportado_en_proceso_mismo_serial():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (17439, "RPC-20260821-00099", "en_revision", "449886745606242304"),
    ]
    hit = primer_reportado_en_proceso_mismo_serial(db, "449886745606242304")
    assert hit is not None
    assert hit[0] == 17439
    assert hit[1] == "RPC-20260821-00099"
    assert hit[2] == "en_revision"


def test_primer_reportado_en_proceso_sin_match():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (1, "RPC-X", "en_revision", "111111111111111111"),
    ]
    assert primer_reportado_en_proceso_mismo_serial(db, "449886745606242304") is None
