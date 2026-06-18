from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.prestamo import Prestamo


def _load_routes_module():
    deps_stub = types.ModuleType("app.core.deps")
    deps_stub.get_current_user = lambda: None
    auth_stub = types.ModuleType("app.schemas.auth")
    auth_stub.UserResponse = type("UserResponse", (), {})
    original_deps = sys.modules.get("app.core.deps")
    original_auth = sys.modules.get("app.schemas.auth")
    sys.modules["app.core.deps"] = deps_stub
    sys.modules["app.schemas.auth"] = auth_stub
    try:
        routes_path = (
            Path(__file__).resolve().parents[1]
            / "app/api/v1/endpoints/pagos_con_errores/routes.py"
        )
        spec = importlib.util.spec_from_file_location(
            "pagos_con_errores_routes_under_test",
            routes_path,
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if original_deps is None:
            sys.modules.pop("app.core.deps", None)
        else:
            sys.modules["app.core.deps"] = original_deps
        if original_auth is None:
            sys.modules.pop("app.schemas.auth", None)
        else:
            sys.modules["app.schemas.auth"] = original_auth


_routes = _load_routes_module()
_resolver_prestamo_id_para_mover_a_cartera = (
    _routes._resolver_prestamo_id_para_mover_a_cartera
)
_validar_prestamo_payload_o_400 = _routes._validar_prestamo_payload_o_400


class _Db:
    def __init__(self, prestamos: dict[int, SimpleNamespace]) -> None:
        self._prestamos = prestamos

    def get(self, model, pk):
        assert model is Prestamo
        return self._prestamos.get(int(pk))


def test_resolver_rechaza_prestamo_hint_de_otra_cedula() -> None:
    db = _Db({10: SimpleNamespace(id=10, cedula="V22222222", estado="APROBADO")})

    prestamo_id, error = _resolver_prestamo_id_para_mover_a_cartera(
        db, "V11111111", 10
    )

    assert prestamo_id is None
    assert error is not None
    assert "id=10" in error
    assert "V22222222" in error
    assert "V11111111" in error


def test_resolver_rechaza_prestamo_hint_no_aprobado() -> None:
    db = _Db({10: SimpleNamespace(id=10, cedula="V11111111", estado="LIQUIDADO")})

    prestamo_id, error = _resolver_prestamo_id_para_mover_a_cartera(
        db, "V11111111", 10
    )

    assert prestamo_id is None
    assert error is not None
    assert "no está APROBADO" in error


def test_resolver_acepta_prestamo_hint_misma_cedula_aprobado() -> None:
    db = _Db({10: SimpleNamespace(id=10, cedula="V11111111", estado="APROBADO")})

    prestamo_id, error = _resolver_prestamo_id_para_mover_a_cartera(
        db, "V11111111", 10
    )

    assert prestamo_id == 10
    assert error is None


def test_payload_validation_rechaza_prestamo_de_otra_cedula() -> None:
    db = _Db({10: SimpleNamespace(id=10, cedula="V22222222", estado="APROBADO")})

    with pytest.raises(HTTPException) as exc:
        _validar_prestamo_payload_o_400(db, 10, "V11111111")

    assert exc.value.status_code == 400
    assert "V22222222" in str(exc.value.detail)
