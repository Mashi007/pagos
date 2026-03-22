"""
Fallar si FastAPI registra el mismo (metodo HTTP, path) mas de una vez.
Evita rutas duplicadas que dejan codigo muerto o comportamiento impredecible.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.mark.unit
def test_no_duplicate_http_method_and_path():
    from app.main import app

    by: dict[tuple[str, str], list[str]] = defaultdict(list)
    for route in app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        for method in route.methods:
            if method == "HEAD":
                continue
            ep = getattr(route, "endpoint", None)
            name = getattr(ep, "__name__", repr(ep))
            by[(method, route.path)].append(name)

    dups = {k: v for k, v in by.items() if len(v) > 1}
    assert not dups, f"Rutas duplicadas (metodo, path): {dups}"


@pytest.mark.unit
def test_openapi_schema_builds():
    """OpenAPI debe generarse sin excepcion (detecta muchos errores de modelos/rutas)."""
    from app.main import app

    schema = app.openapi()
    assert "paths" in schema
    assert len(schema.get("paths", {})) > 0
