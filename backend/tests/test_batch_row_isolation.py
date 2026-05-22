# -*- coding: utf-8 -*-
"""Regression tests for per-row isolation in payment batch mutations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.api.v1.endpoints.pagos import routes as pagos_routes
from app.api.v1.endpoints.pagos.routes import (
    ConciliarAplicarBatchBody,
    conciliar_y_aplicar_pagos_batch,
)
from app.api.v1.endpoints.pagos_con_errores import routes as pce_routes
from app.api.v1.endpoints.pagos_con_errores.routes import (
    EliminarPorDescargaBody,
    mover_a_pagos_normales,
)
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError


class _MoverFakeDb:
    def __init__(self) -> None:
        self.rows = {
            1: self._row(1, "DOC-OK"),
            2: self._row(2, "DOC-FAIL"),
        }
        self.pending_added = []
        self.pending_deleted = []
        self.committed_docs = []
        self.commits = 0
        self.rollbacks = 0
        self._next_pago_id = 100

    @staticmethod
    def _row(row_id: int, doc: str) -> SimpleNamespace:
        return SimpleNamespace(
            id=row_id,
            cedula_cliente="V12345678",
            prestamo_id=None,
            fecha_pago=datetime(2026, 1, 1),
            monto_pagado=Decimal("10.00"),
            numero_documento=doc,
            institucion_bancaria="BNC",
            estado="PENDIENTE",
            conciliado=False,
            notas=None,
            referencia_pago=doc,
        )

    def get(self, model, row_id: int):
        assert model is PagoConError
        return self.rows.get(row_id)

    def add(self, obj) -> None:
        self.pending_added.append(obj)

    def flush(self) -> None:
        for obj in self.pending_added:
            if getattr(obj, "numero_documento", None) == "DOC-FAIL":
                raise RuntimeError("simulated insert failure")
            if getattr(obj, "id", None) is None:
                obj.id = self._next_pago_id
                self._next_pago_id += 1

    def refresh(self, _obj) -> None:
        return None

    def delete(self, row) -> None:
        self.pending_deleted.append(row.id)

    def commit(self) -> None:
        self.commits += 1
        self.committed_docs.extend(
            getattr(obj, "numero_documento", None) for obj in self.pending_added
        )
        for row_id in self.pending_deleted:
            self.rows.pop(row_id, None)
        self.pending_added.clear()
        self.pending_deleted.clear()

    def rollback(self) -> None:
        self.rollbacks += 1
        self.pending_added.clear()
        self.pending_deleted.clear()


def test_mover_a_pagos_commits_successful_rows_before_later_failure(monkeypatch):
    db = _MoverFakeDb()
    monkeypatch.setattr(pce_routes, "pago_con_error_ya_cargado_estricto", lambda *_: None)
    monkeypatch.setattr(pce_routes, "numero_documento_ya_registrado", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(pce_routes, "resolver_cedula_almacenada_en_clientes", lambda *_: "V12345678")

    out = mover_a_pagos_normales(EliminarPorDescargaBody(ids=[1, 2]), db=db)

    assert out["movidos"] == 1
    assert db.committed_docs == ["DOC-OK"]
    assert 1 not in db.rows
    assert 2 in db.rows
    assert db.rollbacks == 1
    assert any("simulated insert failure" in err for err in out["errores"])


class _ConciliarFakeDb:
    def __init__(self) -> None:
        self.payments = {
            1: self._payment(1),
            2: self._payment(2),
        }
        self._pending_originals = {}
        self.committed_ids = []
        self.rollbacks = 0

    @staticmethod
    def _payment(payment_id: int) -> SimpleNamespace:
        return SimpleNamespace(
            id=payment_id,
            prestamo_id=55,
            monto_pagado=Decimal("10.00"),
            estado="PENDIENTE",
            conciliado=False,
            verificado_concordancia="",
            fecha_conciliacion=None,
        )

    def get(self, model, payment_id: int):
        assert model is Pago
        payment = self.payments.get(payment_id)
        if payment is not None and payment_id not in self._pending_originals:
            self._pending_originals[payment_id] = {
                "estado": payment.estado,
                "conciliado": payment.conciliado,
                "verificado_concordancia": payment.verificado_concordancia,
                "fecha_conciliacion": payment.fecha_conciliacion,
            }
        return payment

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed_ids.extend(self._pending_originals)
        self._pending_originals.clear()

    def rollback(self) -> None:
        self.rollbacks += 1
        for payment_id, original in self._pending_originals.items():
            payment = self.payments[payment_id]
            for field, value in original.items():
                setattr(payment, field, value)
        self._pending_originals.clear()


def test_conciliar_batch_keeps_earlier_commit_when_later_row_fails(monkeypatch):
    db = _ConciliarFakeDb()
    monkeypatch.setattr(pagos_routes, "pago_tiene_aplicaciones_cuotas", lambda *_: False)

    def _aplicar(pago, _db):
        if pago.id == 2:
            raise RuntimeError("simulated cascade failure")
        return 1, 0

    monkeypatch.setattr(pagos_routes, "_aplicar_pago_a_cuotas_interno", _aplicar)

    out = conciliar_y_aplicar_pagos_batch(
        ConciliarAplicarBatchBody(ids=[1, 2]),
        db=db,
        current_user=SimpleNamespace(id=1),
    )

    assert out["procesados"] == 1
    assert out["cuotas_aplicadas"] == 1
    assert db.committed_ids == [1]
    assert db.rollbacks == 1
    assert db.payments[1].estado == "PAGADO"
    assert db.payments[1].conciliado is True
    assert db.payments[2].estado == "PENDIENTE"
    assert db.payments[2].conciliado is False
    assert any("simulated cascade failure" in err for err in out["errores"])
