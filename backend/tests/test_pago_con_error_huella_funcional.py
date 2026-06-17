"""Huella funcional y bloqueo de serial duplicado en PagoConError."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.pago_huella_funcional import (
    HTTP_409_DETAIL_DOCUMENTO_DUPLICADO,
    conflicto_huella_pago_con_error_para_prestamo,
    conflicto_serial_para_formulario,
    pago_con_error_conflicto_huella_existente,
    rechazar_si_pago_con_error_serial_duplicado,
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


def test_mover_precheck_usa_prestamo_destino_para_huella() -> None:
    row = SimpleNamespace(
        prestamo_id=None,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=Decimal("96.00"),
        numero_documento="BNC/164458244",
        referencia_pago="164458244",
    )

    msg = conflicto_huella_pago_con_error_para_prestamo(
        _FakeDb(501),
        row,
        prestamo_id_destino=1443,
    )

    assert msg is not None
    assert "pagos.id=501" in msg


def test_pago_con_error_detecta_conflicto_huella() -> None:
    row = SimpleNamespace(
        prestamo_id=1443,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=Decimal("96.00"),
        numero_documento="164458244",
        referencia_pago="164458244",
    )
    assert pago_con_error_conflicto_huella_existente(_FakeDb(501), row) == 501


def test_rechazar_si_documento_duplicado(monkeypatch) -> None:
    row = SimpleNamespace(
        prestamo_id=1443,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=Decimal("96.00"),
        numero_documento="164458244",
        referencia_pago="164458244",
    )

    def _doc_dup(*_a, **_k):
        return True

    monkeypatch.setattr(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        _doc_dup,
    )
    monkeypatch.setattr(
        "app.services.pago_numero_documento.pago_huerfano_adoptable_por_documento",
        lambda *_a, **_k: None,
    )

    with pytest.raises(HTTPException) as exc:
        rechazar_si_pago_con_error_serial_duplicado(_FakeDb(None), row, exclude_pago_con_error_id=1)
    assert exc.value.status_code == 409
    assert exc.value.detail == HTTP_409_DETAIL_DOCUMENTO_DUPLICADO


def test_rechazar_si_huella_duplicada(monkeypatch) -> None:
    row = SimpleNamespace(
        prestamo_id=1443,
        fecha_pago=datetime(2025, 8, 11),
        monto_pagado=Decimal("96.00"),
        numero_documento="164458244",
        referencia_pago="164458244",
    )

    monkeypatch.setattr(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.pago_numero_documento.pago_huerfano_adoptable_por_documento",
        lambda *_a, **_k: None,
    )

    with pytest.raises(HTTPException) as exc:
        rechazar_si_pago_con_error_serial_duplicado(_FakeDb(501), row)
    assert exc.value.status_code == 409
    assert "pagos.id=501" in str(exc.value.detail)


def test_conflicto_serial_adopta_huerfano(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "app.services.pago_numero_documento.primer_pago_cartera_por_documento",
        lambda *_a, **_k: (77, None),
    )
    monkeypatch.setattr(
        "app.services.pago_numero_documento.pago_huerfano_adoptable_por_documento",
        lambda *_a, **_k: 77,
    )

    out = conflicto_serial_para_formulario(
        _FakeDb(None),
        numero_documento="103328178",
        prestamo_id=1443,
        cedula_cliente="V17037221",
    )
    assert out["documento_conflicto"] is True
    assert out["puede_adoptar_pago_huerfano"] is True
    assert out["adoptar_pago_huerfano_id"] == 77
    assert out["documento_bloquea_guardar"] is False
    assert out["conflicto"] is False


def test_conflicto_serial_para_formulario_huella(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pago_numero_documento.numero_documento_ya_registrado",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.pago_numero_documento.primer_pago_cartera_por_documento",
        lambda *_a, **_k: (None, None),
    )

    out = conflicto_serial_para_formulario(
        _FakeDb(88),
        numero_documento="164458244",
        prestamo_id=1443,
        fecha_pago=date(2025, 8, 11),
        monto_pagado=96.0,
        referencia_pago="164458244",
    )
    assert out["documento_conflicto"] is False
    assert out["huella_conflicto"] is True
    assert out["conflicto"] is True
    assert out["huella_pago_id"] == 88
