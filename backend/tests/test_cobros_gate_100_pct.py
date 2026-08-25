# -*- coding: utf-8 -*-
"""Gate Cobros 100%: Gemini true + cero obs + monto < 600."""

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import reportados_validadores_helpers as validadores


def _item(
    *,
    gemini: str | None = "true",
    obs: str = "",
    monto: float = 85,
    moneda: str = "USD",
    duplicado: bool = False,
    estado: str = "pendiente",
):
    return SimpleNamespace(
        estado=estado,
        monto=monto,
        moneda=moneda,
        duplicado_en_pagos=duplicado,
        observacion=obs,
        institucion_financiera="BNC",
        prestamo_duplicado_es_objetivo=False,
        gemini_coincide_exacto=gemini,
    )


def test_gemini_false_obs_vacia_falla():
    """Cambio de comportamiento: ya no autoaprueba sin Gemini true."""
    assert validadores._item_falla_validadores_cola_manual(_item(gemini="false")) is True
    motivos = validadores.motivos_falla_validadores_cola_manual(_item(gemini="false"))
    assert any("Gemini" in m for m in motivos)


def test_gemini_null_o_vacio_falla():
    assert validadores._item_falla_validadores_cola_manual(_item(gemini=None)) is True
    assert validadores._item_falla_validadores_cola_manual(_item(gemini="")) is True
    assert validadores._item_falla_validadores_cola_manual(_item(gemini="error")) is True


def test_gemini_true_obs_vacia_monto_bajo_cumple():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item(gemini="true", obs="", monto=85)
        )
        is False
    )
    assert validadores.motivos_falla_validadores_cola_manual(
        _item(gemini="true", obs="", monto=85)
    ) == []


def test_gemini_true_monto_600_falla():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item(gemini="true", obs="", monto=600)
        )
        is True
    )
    motivos = validadores.motivos_falla_validadores_cola_manual(
        _item(gemini="true", obs="", monto=600)
    )
    assert any("600" in m for m in motivos)


def test_gemini_true_no_clientes_falla():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item(gemini="true", obs="NO CLIENTES")
        )
        is True
    )


def test_gemini_true_duplicado_falla():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item(gemini="true", obs="", duplicado=True)
        )
        is True
    )


def test_en_revision_siempre_falla():
    assert (
        validadores._item_falla_validadores_cola_manual(
            _item(gemini="true", obs="", estado="en_revision")
        )
        is True
    )
