# -*- coding: utf-8 -*-
"""Constraint ck_finiquito_casos_estado debe incluir REVISION_CONTABLE."""

from app.api.v1.endpoints.finiquito.routes import _mensaje_error_integridad_estado_finiquito


class _Orig:
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


class _FakeIntegrityError(Exception):
    orig = _Orig("new row violates check constraint ck_finiquito_casos_estado")


def test_mensaje_integridad_revision_contable():
    msg = _mensaje_error_integridad_estado_finiquito(
        _FakeIntegrityError(),  # type: ignore[arg-type]
        "REVISION_CONTABLE",
    )
    assert "REVISION_CONTABLE" in msg
    assert "075_finiquito_estado_revision_contable" in msg
