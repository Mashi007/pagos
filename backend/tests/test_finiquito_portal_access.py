# -*- coding: utf-8 -*-
"""Comprobaciones de autorizacion portal Finiquito por cedula."""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.endpoints.finiquito import (
    _caso_pertenece_a_portal,
    _cedula_portal_token_normalizada,
)


def test_cedula_portal_token_normalizada_strip_upper():
    fu = SimpleNamespace(cedula="  ab12  ")
    assert _cedula_portal_token_normalizada(fu) == "AB12"


def test_caso_pertenece_a_portal_misma_cedula_distinto_case():
    fu = SimpleNamespace(cedula="v12345678")
    caso = SimpleNamespace(cedula="V12345678")
    assert _caso_pertenece_a_portal(fu, caso) is True


def test_caso_pertenece_a_portal_cedula_distinta():
    fu = SimpleNamespace(cedula="V11111111")
    caso = SimpleNamespace(cedula="V22222222")
    assert _caso_pertenece_a_portal(fu, caso) is False


def test_caso_pertenece_a_portal_usuario_sin_cedula():
    fu = SimpleNamespace(cedula=None)
    caso = SimpleNamespace(cedula="V1")
    assert _caso_pertenece_a_portal(fu, caso) is False
