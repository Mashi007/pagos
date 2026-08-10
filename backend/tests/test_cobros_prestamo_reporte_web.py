# -*- coding: utf-8 -*-
"""Elegibilidad de prestamo para reporte web (solo APROBADO)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.cobros.cobros_publico_reporte_service import (
    error_si_no_puede_reportar_en_web,
    prestamos_aprobados_del_cliente,
    resolver_prestamo_id_para_aprobar_reportado,
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


def test_aprobar_staff_unico_cerrado_ok(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.cobros.cobros_publico_reporte_service.prestamos_aprobados_del_cliente",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "app.services.cobros.cobros_publico_reporte_service.prestamos_cerrados_staff_del_cliente",
        lambda *_a, **_k: [88],
    )
    staff = SimpleNamespace(rol="operator", is_admin=False)
    assert resolver_prestamo_id_para_aprobar_reportado(db, 1, user=staff) == 88


def test_aprobar_staff_varios_cerrados_no_adivina(monkeypatch):
    """Regresion: no aplicar el pago al credito cerrado mas reciente a ciegas."""
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.cobros.cobros_publico_reporte_service.prestamos_aprobados_del_cliente",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "app.services.cobros.cobros_publico_reporte_service.prestamos_cerrados_staff_del_cliente",
        lambda *_a, **_k: [80, 50],
    )
    staff = SimpleNamespace(rol="admin", is_admin=True)
    with pytest.raises(HTTPException) as ei:
        resolver_prestamo_id_para_aprobar_reportado(db, 1, user=staff)
    assert ei.value.status_code == 400
    assert "mas de un credito" in str(ei.value.detail).lower()
