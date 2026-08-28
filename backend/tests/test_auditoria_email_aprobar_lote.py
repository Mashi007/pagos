# -*- coding: utf-8 -*-
"""Aprobación en lote Recibos Auditoría Email."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.auditoria_email.receipts_service import aprobar_recibos_lote


def test_aprobar_lote_clasifica_ok_revision_error():
    db = MagicMock()

    def fake_aprobar(_db, rid):
        if rid == 1:
            return {"ok": True, "status": "approved", "pagoId": 10}
        if rid == 2:
            return {
                "ok": False,
                "status": "revision",
                "motivo": "validacion",
                "pagoErrorId": 20,
            }
        if rid == 3:
            return {"ok": False, "motivo": "exception", "error": "boom"}
        return {"ok": False, "motivo": "estado_no_pending (approved)", "already": True}

    with patch(
        "app.services.auditoria_email.receipts_service.aprobar_recibo",
        side_effect=fake_aprobar,
    ):
        out = aprobar_recibos_lote(db, [1, 2, 3, 4, 1])

    assert out["total"] == 4
    assert out["aprobados"] == 1
    assert out["revision"] == 1
    assert out["errores"] == 1
    assert out["omitidos"] == 1
    assert out["redirectRevision"]
