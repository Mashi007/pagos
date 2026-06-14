# -*- coding: utf-8 -*-
"""Traslados entre bandejas finiquito: solo administrador."""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.endpoints.finiquito.routes import (
    _error_gestion_bandeja_finiquito_si_no_admin,
    _error_traslado_finiquito_si_no_admin,
    _traslado_finiquito_requiere_admin,
)


def test_traslado_requiere_admin_bandeja_a_revision():
    assert _traslado_finiquito_requiere_admin("REVISION", "ACEPTADO") is True


def test_traslado_requiere_admin_revision_a_contable():
    assert _traslado_finiquito_requiere_admin("ACEPTADO", "REVISION_CONTABLE") is True


def test_traslado_requiere_admin_contable_a_trabajo():
    assert _traslado_finiquito_requiere_admin("REVISION_CONTABLE", "EN_PROCESO") is True


def test_aceptado_a_trabajo_directo_ya_no_requiere_admin():
    assert _traslado_finiquito_requiere_admin("ACEPTADO", "EN_PROCESO") is False


def test_volver_validacion_desde_trabajo_no_requiere_admin():
    assert _traslado_finiquito_requiere_admin("EN_PROCESO", "ACEPTADO") is False


def test_operario_denegado_traslado():
    operario = SimpleNamespace(rol="operator")
    assert (
        _error_traslado_finiquito_si_no_admin(operario, "REVISION", "ACEPTADO")
        is not None
    )


def test_admin_permitido_traslado():
    admin = SimpleNamespace(rol="admin")
    assert _error_traslado_finiquito_si_no_admin(admin, "REVISION", "ACEPTADO") is None


def test_operario_denegado_gestion_bandeja():
    operario = SimpleNamespace(rol="operator")
    assert _error_gestion_bandeja_finiquito_si_no_admin(operario) is not None


def test_admin_permitido_gestion_bandeja():
    admin = SimpleNamespace(rol="admin")
    assert _error_gestion_bandeja_finiquito_si_no_admin(admin) is None
