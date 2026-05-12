# -*- coding: utf-8 -*-
"""Regresiones para reintentos idempotentes en cambios de estado de Cobros."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros.routes import CambiarEstadoBody, cambiar_estado_pago


def _db_con_pago_reportado(pr: SimpleNamespace) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = pr
    return db


def test_reintento_rechazado_mismo_estado_no_reenvia_correo_ni_historial():
    pr = SimpleNamespace(
        id=123,
        estado="rechazado",
        motivo_rechazo="Comprobante duplicado",
        referencia_interna="RPC-123",
    )
    db = _db_con_pago_reportado(pr)

    with (
        patch("app.api.v1.endpoints.cobros.routes.send_email") as send_email,
        patch("app.api.v1.endpoints.cobros.routes._registrar_historial") as registrar_historial,
    ):
        resp = cambiar_estado_pago(
            123,
            CambiarEstadoBody(estado="rechazado", motivo="Comprobante duplicado"),
            db=db,
            current_user={"id": 7, "email": "operador@example.com"},
        )

    assert resp == {
        "ok": True,
        "mensaje": "El pago reportado ya estaba en estado rechazado.",
    }
    send_email.assert_not_called()
    registrar_historial.assert_not_called()
    db.commit.assert_not_called()
