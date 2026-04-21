# -*- coding: utf-8 -*-
"""Cobertura del matcher de rutas del middleware de sobre-aplicación."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware.validador_sobre_aplicacion import (
    ValidadorSobreAplicacionMiddleware,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _build_request(path: str, method: str = "POST") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


@pytest.mark.anyio
async def test_middleware_detecta_aplicar_cuotas_y_aplicar_pagos_cuotas():
    mw = ValidadorSobreAplicacionMiddleware(app=lambda *args, **kwargs: None)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=200)

    fake_db = MagicMock()
    fake_db.close = MagicMock()

    with patch(
        "app.middleware.validador_sobre_aplicacion.SessionLocal",
        return_value=fake_db,
    ) as mock_session_local:
        r1 = await mw.dispatch(_build_request("/api/v1/pagos/10/aplicar-cuotas"), call_next)
        r2 = await mw.dispatch(_build_request("/api/v1/pagos/por-prestamo/10/aplicar-pagos-cuotas"), call_next)

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Debe abrir sesión para validar en rutas de aplicación.
    assert mock_session_local.call_count == 2
    assert fake_db.close.call_count == 2


@pytest.mark.anyio
async def test_middleware_no_valida_ruta_no_aplicacion():
    mw = ValidadorSobreAplicacionMiddleware(app=lambda *args, **kwargs: None)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=200)

    with patch("app.middleware.validador_sobre_aplicacion.SessionLocal") as mock_session_local:
        resp = await mw.dispatch(_build_request("/api/v1/pagos/10"), call_next)

    assert resp.status_code == 200
    mock_session_local.assert_not_called()
