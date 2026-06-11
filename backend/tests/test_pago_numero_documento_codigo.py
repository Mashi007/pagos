# -*- coding: utf-8 -*-
"""Con código §CD: no debe bloquear por evasión del serial base."""

from __future__ import annotations

from app.core.documento import compose_numero_documento_almacenado
from app.services.pago_numero_documento import (
    documento_almacenado_tiene_codigo_desambiguacion,
    numero_documento_ya_registrado,
)


class _FakeDb:
    def scalar(self, _q):
        return None


def test_documento_con_codigo_detecta_sufijo():
    doc = compose_numero_documento_almacenado("740087401373233", "A2637")
    assert doc is not None
    assert documento_almacenado_tiene_codigo_desambiguacion(doc) is True


def test_documento_sin_codigo_no_tiene_sufijo():
    assert documento_almacenado_tiene_codigo_desambiguacion("740087401373233") is False


def test_numero_documento_con_codigo_no_consulta_evasion(monkeypatch):
    evasion_calls: list[str] = []

    def _evasion(_db, doc, **_kw):
        evasion_calls.append(str(doc))
        return True

    monkeypatch.setattr(
        "app.services.pago_numero_documento.documento_colisiona_evasion_registrado",
        _evasion,
    )

    doc = compose_numero_documento_almacenado("740087401373233", "A2637")
    assert numero_documento_ya_registrado(_FakeDb(), doc) is False
    assert evasion_calls == []
