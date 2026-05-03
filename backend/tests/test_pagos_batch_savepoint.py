# -*- coding: utf-8 -*-
"""Regression tests for batch payment reconciliation transaction isolation."""
from __future__ import annotations

from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace


def test_conciliar_aplicar_batch_uses_row_savepoint_not_full_rollback(monkeypatch):
    from app.api.v1.endpoints.pagos import routes

    class FakeSession:
        def __init__(self) -> None:
            self.rows = {
                1: SimpleNamespace(
                    id=1,
                    estado="PENDIENTE",
                    prestamo_id=10,
                    monto_pagado=Decimal("100.00"),
                    conciliado=False,
                    verificado_concordancia=None,
                    fecha_conciliacion=None,
                ),
                2: SimpleNamespace(
                    id=2,
                    estado="PENDIENTE",
                    prestamo_id=10,
                    monto_pagado=Decimal("100.00"),
                    conciliado=False,
                    verificado_concordancia=None,
                    fecha_conciliacion=None,
                ),
            }
            self.flush_count = 0
            self.commit_count = 0
            self.rollback_count = 0
            self.savepoint_count = 0

        def begin_nested(self):
            self.savepoint_count += 1
            return nullcontext()

        def get(self, _model, row_id):
            return self.rows.get(row_id)

        def flush(self):
            self.flush_count += 1

        def commit(self):
            self.commit_count += 1

        def rollback(self):
            self.rollback_count += 1

    db = FakeSession()

    monkeypatch.setattr(routes, "pago_tiene_aplicaciones_cuotas", lambda _db, _pago_id: False)

    def aplicar_o_fallar(pago, _db):
        if pago.id == 2:
            raise RuntimeError("boom")
        return 1, 0

    monkeypatch.setattr(routes, "_aplicar_pago_a_cuotas_interno", aplicar_o_fallar)

    result = routes.conciliar_y_aplicar_pagos_batch(
        routes.ConciliarAplicarBatchBody(ids=[1, 2]),
        db=db,
        current_user=object(),
    )

    assert result["procesados"] == 1
    assert result["cuotas_aplicadas"] == 1
    assert len(result["errores"]) == 1
    assert db.savepoint_count == 2
    assert db.rollback_count == 0
    assert db.commit_count == 1
