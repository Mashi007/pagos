# -*- coding: utf-8 -*-
"""Elegibilidad de préstamo para reporte web (APROBADO / LIQUIDADO único)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.cobros.cobros_publico_reporte_service import (
    error_si_no_puede_reportar_en_web,
    prestamos_aprobados_del_cliente,
)


def _mock_db_rows(rows: list[tuple[int, str]]) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.all.return_value = rows
    return db


def test_prefiere_aprobado_sobre_liquidado():
    db = _mock_db_rows([(10, "LIQUIDADO"), (20, "APROBADO")])
    assert prestamos_aprobados_del_cliente(db, 1) == [20]


def test_un_solo_liquidado_sin_aprobado():
    db = _mock_db_rows([(3412, "LIQUIDADO")])
    assert prestamos_aprobados_del_cliente(db, 1) == [3412]
    assert error_si_no_puede_reportar_en_web([3412]) is None


def test_varios_liquidado_error():
    ids = [1, 2]
    err = error_si_no_puede_reportar_en_web(ids)
    assert err is not None
    assert "más de un crédito" in err


def test_sin_operativos_error():
    err = error_si_no_puede_reportar_en_web([])
    assert err is not None
    assert "No tiene un crédito activo" in err
