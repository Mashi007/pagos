# -*- coding: utf-8 -*-
"""Mensajes y detección de errores de sesión al reaplicar cascada."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError, PendingRollbackError

from app.services.pagos_aplicacion_prestamo import (
    _db_error_aborta_transaccion,
    detalle_excepcion_db,
)


def test_detalle_excepcion_db_prioriza_causa_psycopg():
    raiz = IntegrityError("stmt", {}, Exception("duplicate key value violates unique constraint"))
    envoltorio = PendingRollbackError(
        "This Session's transaction has been rolled back due to a previous exception during flush."
    )
    envoltorio.__cause__ = raiz

    msg = detalle_excepcion_db(envoltorio)

    assert "duplicate key" in msg
    assert "Causa:" in msg


def test_db_error_aborta_transaccion_con_pending_rollback():
    assert _db_error_aborta_transaccion(PendingRollbackError("rolled back"))


def test_db_error_aborta_transaccion_con_sqlalchemy():
    assert _db_error_aborta_transaccion(IntegrityError("x", {}, Exception("fk")))


def test_db_error_no_aborta_value_error_negocio():
    assert not _db_error_aborta_transaccion(ValueError("Suma aplicada supera monto"))


class _FakeBatchDB:
    def __init__(self, pagos):
        self._pagos = {int(p.id): p for p in pagos}
        self.events: list[str] = []

    def get(self, _model, model_id):
        return self._pagos.get(int(model_id))

    def flush(self):
        self.events.append("flush")

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")


def test_conciliar_aplicar_batch_confirma_fila_exitosa_antes_de_rollback(monkeypatch):
    import app.api.v1.endpoints.pagos.routes as pagos_routes

    pago_ok = SimpleNamespace(
        id=101,
        estado="PENDIENTE",
        prestamo_id=55,
        monto_pagado=100,
        conciliado=False,
        verificado_concordancia="",
        fecha_conciliacion=None,
    )
    pago_error = SimpleNamespace(
        id=102,
        estado="PENDIENTE",
        prestamo_id=55,
        monto_pagado=100,
        conciliado=False,
        verificado_concordancia="",
        fecha_conciliacion=None,
    )
    db = _FakeBatchDB([pago_ok, pago_error])

    monkeypatch.setattr(
        pagos_routes,
        "pago_tiene_aplicaciones_cuotas",
        lambda *_args, **_kwargs: False,
    )

    def _aplicar_o_fallar(pago, _db):
        if int(pago.id) == 102:
            raise RuntimeError("fallo simulado")
        return 1, 0

    monkeypatch.setattr(
        pagos_routes,
        "_aplicar_pago_a_cuotas_interno",
        _aplicar_o_fallar,
    )

    res = pagos_routes.conciliar_y_aplicar_pagos_batch(
        pagos_routes.ConciliarAplicarBatchBody(ids=[101, 102]),
        db=db,
        current_user=SimpleNamespace(id=1),
    )

    assert res["procesados"] == 1
    assert len(res["errores"]) == 1
    assert db.events.index("commit") < db.events.index("rollback")
