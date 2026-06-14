# -*- coding: utf-8 -*-
"""Sincronizacion prestamos.estado_gestion_finiquito vs finiquito_casos.estado."""

from __future__ import annotations

from app.services.finiquito_prestamo_gestion_sync import _VALORES_GESTION_EN_PRESTAMO


def test_valores_gestion_incluyen_fases_intermedias():
    assert _VALORES_GESTION_EN_PRESTAMO == frozenset(
        {
            "REVISION",
            "ACEPTADO",
            "REVISION_CONTABLE",
            "EN_PROCESO",
            "TERMINADO",
        }
    )


def test_rechazado_no_se_refleja_en_prestamo():
    assert "RECHAZADO" not in _VALORES_GESTION_EN_PRESTAMO
