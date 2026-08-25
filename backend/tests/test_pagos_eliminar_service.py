# -*- coding: utf-8 -*-
"""Tests eliminación de pagos (coordination + servicio)."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pagos_eliminar_coordinacion import (
    eliminacion_activa,
    eliminacion_context,
)


def test_eliminacion_context_marca_prestamo():
    assert not eliminacion_activa(99)
    with eliminacion_context(99):
        assert eliminacion_activa(99)
    assert not eliminacion_activa(99)


def test_ejecutar_eliminar_pago_espera_cascada_activa():
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 3202
    db = MagicMock()
    db.get.return_value = row

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=True,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={"en_proceso": True},
    ), patch(
        "app.services.revision_manual_cascada_bg.esperar_fin_cascada_bg",
        return_value=True,
    ) as esperar, patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": False},
    ):
        result = ejecutar_eliminar_pago(db, 95521, current_user=None)
        esperar.assert_called_once()
        assert result["ok"] is True
        db.commit.assert_called()
