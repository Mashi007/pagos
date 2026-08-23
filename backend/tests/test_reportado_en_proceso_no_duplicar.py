"""Aviso: recibo ya en cola Cobros no debe duplicarse."""
from unittest.mock import MagicMock, patch

from app.services.cobros.pago_reportado_documento import (
    CODIGO_PAGO_EN_PROCESO,
    MSG_NO_INGRESAR_PAGO_EN_PROCESO,
    MSG_PAGO_EN_PROCESO_ADMIN,
    detalle_bloqueo_comprobante_en_proceso,
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


def test_detalle_bloqueo_si_reportado_en_cola():
    db = MagicMock()
    with patch(
        "app.services.cobros.pago_reportado_documento.primer_reportado_en_proceso_mismo_serial",
        return_value=(9, "RPC-1", "pendiente"),
    ):
        d = detalle_bloqueo_comprobante_en_proceso(db, "12345")
    assert d is not None
    assert d["codigo"] == CODIGO_PAGO_EN_PROCESO
    assert "procesado" in str(d["message"]).lower()
    assert d["origen"] == "pagos_reportados"
    assert MSG_NO_INGRESAR_PAGO_EN_PROCESO in str(d["message"])


def test_detalle_bloqueo_si_ya_en_pagos():
    db = MagicMock()
    with patch(
        "app.services.cobros.pago_reportado_documento.primer_reportado_en_proceso_mismo_serial",
        return_value=None,
    ), patch(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        return_value=True,
    ), patch(
        "app.services.pago_numero_documento.primer_pago_cartera_por_documento",
        return_value=(88, 12),
    ):
        d = detalle_bloqueo_comprobante_en_proceso(db, "12345")
    assert d is not None
    assert d["codigo"] == CODIGO_PAGO_EN_PROCESO
    assert d["origen"] == "pagos"
    assert d["pago_conflicto_id"] == 88
    assert d["prestamo_conflicto_id"] == 12
