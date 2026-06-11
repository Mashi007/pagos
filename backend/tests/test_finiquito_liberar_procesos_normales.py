# -*- coding: utf-8 -*-
"""Liberar finiquito → cartera operativa (bandeja / área revisión)."""

from __future__ import annotations

from app.services.finiquito_liberar_procesos_normales_service import (
    ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES,
    ejecutar_liberar_finiquito_a_procesos_normales,
)


def test_estados_permitidos_bandeja_y_revision():
    assert "REVISION" in ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES
    assert "ACEPTADO" in ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES
    assert "EN_PROCESO" not in ESTADOS_CASO_LIBERAR_PROCESOS_NORMALES


def test_caso_inexistente():
    class _Db:
        def query(self, _model):
            return self

        def filter(self, *_a, **_k):
            return self

        def first(self):
            return None

    out = ejecutar_liberar_finiquito_a_procesos_normales(_Db(), 999)
    assert out["ok"] is False
    assert out.get("http_status") == 404
