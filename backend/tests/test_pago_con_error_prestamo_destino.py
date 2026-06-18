from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.pagos_con_errores.routes import (
    _resolver_prestamo_id_para_mover_a_cartera,
    _validar_prestamo_payload_o_400,
)
from app.models.prestamo import Prestamo


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
