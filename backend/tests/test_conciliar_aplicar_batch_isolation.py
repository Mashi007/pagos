# -*- coding: utf-8 -*-
"""Regresión: conciliar-aplicar-batch debe aislar fallos por SAVEPOINT, no Session.rollback()."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.pagos.crud_pagos_aplicacion_routes import (
    ConciliarAplicarBatchBody,
    conciliar_y_aplicar_pagos_batch,
)


def _pago(pid: int, **kwargs):
    base = dict(
        id=pid,
        estado="PENDIENTE",
        prestamo_id=100 + pid,
        monto_pagado=50.0,
        conciliado=False,
        verificado_concordancia="NO",
        fecha_conciliacion=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class _FakeSession:
    """Session mínima: SAVEPOINT real (contador) + rollback de sesión rastreado."""

    def __init__(self, pagos: dict[int, SimpleNamespace]):
        self._pagos = pagos
        self.rollback_calls = 0
        self.nested_enter = 0
        self.nested_exit_ok = 0
        self.nested_exit_err = 0
        self.flush_calls = 0
        self.commit_calls = 0

    def get(self, _model, pid):
        return self._pagos.get(int(pid))

    def flush(self):
        self.flush_calls += 1

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1

    @contextmanager
    def begin_nested(self):
        self.nested_enter += 1
        try:
            yield
        except Exception:
            self.nested_exit_err += 1
            raise
        else:
            self.nested_exit_ok += 1


def test_batch_row_failure_does_not_session_rollback_prior_success(monkeypatch):
    """
    Escenario: lote [1, 2]; cascada OK en 1 y ValueError en 2.

    Antes: except llamaba db.rollback() y deshacía la conciliación del pago 1
    aunque el resumen ya lo contaba en `procesados`.
    Ahora: SAVEPOINT revierte solo la fila 2; no hay Session.rollback().
    """
    p1 = _pago(1)
    p2 = _pago(2)
    db = _FakeSession({1: p1, 2: p2})

    def _fake_tiene_apps(_db, pago_id):
        return False

    def _fake_cascada(pago, _db):
        if int(pago.id) == 2:
            raise ValueError("integridad cuota_pagos simulada")
        return 1, 0

    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos.crud_pagos_aplicacion_routes.pago_tiene_aplicaciones_cuotas",
        _fake_tiene_apps,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.pagos.crud_pagos_aplicacion_routes._aplicar_pago_a_cuotas_interno",
        _fake_cascada,
    )

    user = MagicMock()
    result = conciliar_y_aplicar_pagos_batch(
        payload=ConciliarAplicarBatchBody(ids=[1, 2]),
        db=db,
        current_user=user,
    )

    assert db.rollback_calls == 0
    assert db.nested_enter == 2
    assert db.nested_exit_ok == 1
    assert db.nested_exit_err == 1
    assert db.commit_calls == 1

    assert result["procesados"] == 1
    assert result["cuotas_aplicadas"] == 1
    assert len(result["errores"]) == 1
    assert "Pago 2:" in result["errores"][0]

    assert p1.conciliado is True
    assert p1.estado == "PAGADO"
    assert (p1.verificado_concordancia or "").upper() == "SI"

    # Fila 2: el SAVEPOINT falló; en sesión real los attrs se revierten.
    # Aquí el fake no revierte objetos: solo garantizamos que no hubo rollback de sesión.
    assert "integridad cuota_pagos" in result["errores"][0]


def test_batch_empty_ids():
    db = _FakeSession({})
    result = conciliar_y_aplicar_pagos_batch(
        payload=ConciliarAplicarBatchBody(ids=[]),
        db=db,
        current_user=MagicMock(),
    )
    assert result["procesados"] == 0
    assert result["mensaje"].startswith("No hay IDs")
