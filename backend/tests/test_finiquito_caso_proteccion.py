# -*- coding: utf-8 -*-
"""Casos finiquito en flujo activo no deben borrarse por limpieza automática."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.finiquito_caso_cleanup import eliminar_finiquito_casos_si_prestamo_no_liquidado
from app.services.finiquito_caso_proteccion import (
    ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA,
    prestamo_tiene_finiquito_caso_protegido,
)


def test_estados_protegidos_incluyen_area_revision_y_trabajo():
    assert "ACEPTADO" in ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA
    assert "EN_PROCESO" in ESTADOS_CASO_PROTEGIDOS_AUTO_LIMPIEZA


@patch("app.services.finiquito_caso_proteccion.prestamo_tiene_reserva_revision_manual_conciliacion_activa")
@patch("app.services.finiquito_conciliacion_visto_service.prestamo_tiene_reserva_finiquito_activa")
def test_caso_aceptado_protegido_sin_reserva(_visto, _rm):
    _visto.return_value = False
    _rm.return_value = False
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        estado="ACEPTADO"
    )
    assert prestamo_tiene_finiquito_caso_protegido(db, 42) is True


@patch("app.services.finiquito_caso_proteccion.prestamo_tiene_finiquito_caso_protegido")
def test_no_elimina_si_prestamo_aprobado_y_caso_protegido(_protegido):
    _protegido.return_value = True
    db = MagicMock()
    assert eliminar_finiquito_casos_si_prestamo_no_liquidado(db, 7, "APROBADO") == 0
    db.query.assert_not_called()
