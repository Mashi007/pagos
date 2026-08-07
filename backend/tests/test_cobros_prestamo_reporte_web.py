# -*- coding: utf-8 -*-
"""Elegibilidad de prestamo para reporte web (solo APROBADO)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.cobros.cobros_publico_reporte_service import (
    error_si_no_puede_reportar_en_web,
    prestamos_aprobados_del_cliente,
)


def _mock_db_ids(ids: list[int]) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.all.return_value = [(i,) for i in ids]
    return db


def test_solo_aprobados():
    db = _mock_db_ids([20])
    assert prestamos_aprobados_del_cliente(db, 1) == [20]


def test_sin_aprobado_no_permite_liquidado():
    db = _mock_db_ids([])
    assert prestamos_aprobados_del_cliente(db, 1) == []
    err = error_si_no_puede_reportar_en_web([])
    assert err is not None
    assert "no puede cargar" in err.lower() or "APROBADO" in err


def test_varios_aprobado_error():
    ids = [1, 2]
    err = error_si_no_puede_reportar_en_web(ids)
    assert err is not None
    assert "mas de un credito" in err.lower() or "más de un crédito" in err.lower()


def test_un_aprobado_ok():
    assert error_si_no_puede_reportar_en_web([3412]) is None
