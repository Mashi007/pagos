"""Tests de cupo de prestamos APROBADO por prefijo de cedula (E/V=1, J=5)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.prestamos import cupo_cedula_aprobados as cupo_module
from app.services.prestamos.cupo_cedula_aprobados import validar_cupo_nuevo_prestamo_aprobado
from app.utils.cedula_almacenamiento import (
    max_aprobados_permitidos_por_prefijo,
    normalizar_cedula_clave_cupo,
    prefijo_politica_cupo_aprobados,
)


def test_normalizar_clave_cupo_quita_guiones():
    assert normalizar_cedula_clave_cupo("j-40123456-7") == "J401234567"


def test_prefijo_solo_e_v_j():
    assert prefijo_politica_cupo_aprobados("V12345678") == "V"
    assert prefijo_politica_cupo_aprobados("E99887766") == "E"
    assert prefijo_politica_cupo_aprobados("J401234567") == "J"
    assert prefijo_politica_cupo_aprobados("G12345678") is None
    assert prefijo_politica_cupo_aprobados("40123456") is None


def test_max_aprobados_por_prefijo():
    assert max_aprobados_permitidos_por_prefijo("V") == 1
    assert max_aprobados_permitidos_por_prefijo("E") == 1
    assert max_aprobados_permitidos_por_prefijo("J") == 5
    assert max_aprobados_permitidos_por_prefijo("G") is None


@patch("app.services.prestamos.cupo_cedula_aprobados.contar_aprobados_misma_clave_cupo")
def test_validar_cupo_rechaza_prefijo_invalido(mock_contar):
    mock_contar.return_value = 0
    with pytest.raises(HTTPException) as exc:
        validar_cupo_nuevo_prestamo_aprobado(MagicMock(), "G12345678")
    assert exc.value.status_code == 400
    assert "prefijo no permitido" in str(exc.value.detail).lower()
    mock_contar.assert_not_called()


@patch("app.services.prestamos.cupo_cedula_aprobados.contar_aprobados_misma_clave_cupo")
def test_validar_cupo_j_bloquea_sexto(mock_contar):
    mock_contar.return_value = 5
    with pytest.raises(HTTPException) as exc:
        validar_cupo_nuevo_prestamo_aprobado(MagicMock(), "J401234567")
    assert exc.value.status_code == 400
    assert "prefijo J" in str(exc.value.detail)


@patch("app.services.prestamos.cupo_cedula_aprobados.contar_aprobados_misma_clave_cupo")
def test_validar_cupo_v_bloquea_segundo(mock_contar):
    mock_contar.return_value = 1
    with pytest.raises(HTTPException) as exc:
        validar_cupo_nuevo_prestamo_aprobado(MagicMock(), "V22621583")
    assert exc.value.status_code == 400
    assert "prefijo V" in str(exc.value.detail)


@patch("app.services.prestamos.cupo_cedula_aprobados.contar_aprobados_misma_clave_cupo")
def test_validar_cupo_j_permite_segundo(mock_contar):
    mock_contar.return_value = 1
    validar_cupo_nuevo_prestamo_aprobado(MagicMock(), "J99887766")


class _Dialect:
    name = "postgresql"


class _Bind:
    dialect = _Dialect()


class _PostgresSession:
    def __init__(self):
        self.execute_calls = []

    def get_bind(self):
        return _Bind()

    def execute(self, stmt, params=None):
        self.execute_calls.append((str(stmt), params))
        return MagicMock()


@patch("app.services.prestamos.cupo_cedula_aprobados.contar_aprobados_misma_clave_cupo")
def test_validar_cupo_bloquea_clave_en_postgresql_antes_de_contar(mock_contar):
    mock_contar.return_value = 0
    db = _PostgresSession()

    validar_cupo_nuevo_prestamo_aprobado(db, "V-22621583")

    assert db.execute_calls
    sql, params = db.execute_calls[0]
    assert "pg_advisory_xact_lock" in sql
    assert params == {"clave": "V22621583"}
    mock_contar.assert_called_once_with(db, "V22621583", exclude_prestamo_id=None)


@patch.object(cupo_module, "contar_aprobados_misma_clave_cupo")
def test_validar_cupo_no_intenta_bloqueo_fuera_de_postgresql(mock_contar):
    mock_contar.return_value = 0
    db = MagicMock()
    db.get_bind.return_value.dialect.name = "sqlite"

    validar_cupo_nuevo_prestamo_aprobado(db, "V22621583")

    db.execute.assert_not_called()
