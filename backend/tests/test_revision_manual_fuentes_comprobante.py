"""Fuentes de comprobante para Conciliar (pagos + pagos_con_errores + Gmail)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.revision_manual_conciliacion_cartera_service import (
    _iter_fuentes_comprobante_conciliar_revision,
)


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeDb:
    def __init__(self, pagos=None, pces=None, gsi=None):
        self._pagos = pagos or []
        self._pces = pces or []
        self._gsi = gsi or []

    def execute(self, stmt):
        sql = str(stmt).lower()
        if "pagos_gmail_sync_item" in sql:
            return _FakeResult(self._gsi)
        if "pagos_con_errores" in sql:
            return _FakeResult(self._pces)
        if "from pagos" in sql:
            return _FakeResult(self._pagos)
        return _FakeResult([])


def test_iter_fuentes_incluye_gmail_y_pagos_con_error(monkeypatch) -> None:
    prestamo = SimpleNamespace(id=486, cedula="V16370277")
    pagos = [
        SimpleNamespace(
            id=1,
            link_comprobante="https://x/api/v1/pagos/comprobante-imagen/" + "a" * 32,
            documento_ruta=None,
            numero_documento="DOC1",
            referencia_pago="DOC1",
            cedula_cliente="V16370277",
        )
    ]
    pces = [
        SimpleNamespace(
            id=99,
            prestamo_id=None,
            documento_ruta=None,
            numero_documento="REF-PCE",
            referencia_pago="REF-PCE",
            cedula_cliente="V16370277",
        )
    ]
    gsi = [
        SimpleNamespace(
            id=23696,
            cedula="V16370277",
            numero_referencia="384787861658492928",
            drive_link="https://x/api/v1/pagos/comprobante-imagen/" + "b" * 32,
        )
    ]

    def fake_enriquecer(db, items):
        for it in items:
            if (it.get("numero_documento") or "") == "REF-PCE":
                it["link_comprobante"] = (
                    "https://x/api/v1/pagos/comprobante-imagen/" + "c" * 32
                )

    monkeypatch.setattr(
        "app.services.revision_manual_conciliacion_cartera_service.enriquecer_items_link_comprobante_desde_gmail",
        fake_enriquecer,
    )

    db = _FakeDb(pagos=pagos, pces=pces, gsi=gsi)
    fuentes = _iter_fuentes_comprobante_conciliar_revision(db, prestamo)  # type: ignore[arg-type]

    assert len(fuentes) == 3
    assert {f.fuente for f in fuentes} == {"pago", "pago_con_error", "gmail_sync"}
