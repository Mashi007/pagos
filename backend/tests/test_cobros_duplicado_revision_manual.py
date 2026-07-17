"""Regresiones: un serial ya existente siempre requiere decisión manual."""

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import reportados_validadores_helpers as validadores


def _item_duplicado(*, mismo_prestamo: bool):
    return SimpleNamespace(
        estado="pendiente",
        monto=85,
        moneda="USD",
        duplicado_en_pagos=True,
        observacion="",
        institucion_financiera="BNC",
        prestamo_duplicado_es_objetivo=mismo_prestamo,
        gemini_coincide_exacto="true",
    )


def test_duplicado_mismo_prestamo_va_a_revision_manual():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item_duplicado(mismo_prestamo=True)
        )
        is True
    )


def test_duplicado_otro_prestamo_va_a_revision_manual():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item_duplicado(mismo_prestamo=False)
        )
        is True
    )
