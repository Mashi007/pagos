"""Huella funcional al mover PagoConError → pagos."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.pago_huella_funcional import (
    pago_con_error_conflicto_huella_existente,
    ref_norm_desde_campos,
)


class _FakeDb:
    def __init__(self, conflict_id: int | None) -> None:
        self._conflict_id = conflict_id

    def execute(self, _sql, _params):
        if self._conflict_id is None:
            return _EmptyResult()
        return _RowResult(self._conflict_id)

    def scalar(self, _sql):
        return None


class _EmptyResult:
    def first(self):
        return None


class _RowResult:
    def __init__(self, pid: int) -> None:
        self._pid = pid

    def first(self):
        return (self._pid,)


def test_ref_norm_desde_numero_documento() -> None:
    assert ref_norm_desde_campos("164458244", "164458244") == "164458244"


def test_pago_con_error_sin_prestamo_no_conflicto() -> None:
    row = SimpleNamespace(
        prestamo_id=None,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=96.0,
        numero_documento="164458244",
        referencia_pago="164458244",
    )
    assert pago_con_error_conflicto_huella_existente(_FakeDb(99), row) is None


def test_pago_con_error_detecta_conflicto_huella() -> None:
    row = SimpleNamespace(
        prestamo_id=1443,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=Decimal("96.00"),
        numero_documento="164458244",
        referencia_pago="164458244",
    )
    assert pago_con_error_conflicto_huella_existente(_FakeDb(501), row) == 501
