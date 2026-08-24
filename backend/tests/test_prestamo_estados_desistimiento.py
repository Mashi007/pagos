# -*- coding: utf-8 -*-
"""Variantes DESISTIMIENTO / DESESTIMADO / DESISTIDO en exclusiones centralizadas."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.constants.prestamo_estados import (
    ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES,
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
    prestamo_estado_es_desistimiento,
)
from app.services.notificaciones_exclusion_desistimiento import (
    motivo_bloqueo_prestamo_notificacion,
)
from app.services.reporte_cedulas_cuota_hoja import _items_cuotas_para_informe


def test_prestamo_estado_es_desistimiento_variantes():
    for est in ESTADOS_PRESTAMO_DESISTIMIENTO_VARIANTES:
        assert prestamo_estado_es_desistimiento(est) is True
        assert prestamo_estado_es_desistimiento(f" {est.lower()} ") is True
    assert prestamo_estado_es_desistimiento("APROBADO") is False


def test_exclusion_cobranza_incluye_variantes_legacy():
    excl = {e.upper() for e in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF}
    assert "LIQUIDADO" in excl
    assert "DESISTIMIENTO" in excl
    assert "DESESTIMADO" in excl
    assert "DESISTIDO" in excl


def test_motivo_bloqueo_prestamo_desestimado():
    db = MagicMock()
    db.scalar.return_value = "desestimado"
    assert motivo_bloqueo_prestamo_notificacion(db, 20) == "DESESTIMADO"


def test_items_cuotas_informe_sin_mora_si_solo_desistimiento():
    items = [(1, 1, None, 100, 0, None, 12)]
    assert (
        _items_cuotas_para_informe(
            "84491751",
            {"84491751": items},
            {},
            {"84491751": {"DESISTIMIENTO"}},
        )
        == []
    )
