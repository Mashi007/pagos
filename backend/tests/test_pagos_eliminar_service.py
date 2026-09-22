# -*- coding: utf-8 -*-
"""Tests eliminación de pagos (coordination + servicio)."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

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
    row.numero_documento = None
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
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
    ) as lock, patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": False},
    ), patch(
        "app.services.pago_numero_documento.liberar_serial_tras_baja_o_cambio",
    ):
        result = ejecutar_eliminar_pago(db, 95521, current_user=None)
        esperar.assert_called_once()
        lock.assert_called_with(db, 3202)
        assert result["ok"] is True
        db.commit.assert_called()


def test_ejecutar_eliminar_pago_adquiere_lock_antes_de_mutar():
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 2187
    row.numero_documento = None
    db = MagicMock()
    db.get.return_value = row
    order: list[str] = []

    def lock_side_effect(_db, pid):
        order.append(f"lock:{pid}")

    def execute_side_effect(*_a, **_k):
        order.append("execute")
        return MagicMock()

    db.execute.side_effect = execute_side_effect

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={},
    ), patch(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
        side_effect=lock_side_effect,
    ), patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": False},
    ), patch(
        "app.services.pago_numero_documento.liberar_serial_tras_baja_o_cambio",
    ):
        result = ejecutar_eliminar_pago(db, 43300, current_user=None)

    assert result["ok"] is True
    assert order[0] == "lock:2187"
    assert "execute" in order
    assert order.index("lock:2187") < order.index("execute")


def test_ejecutar_eliminar_pago_reintenta_ante_deadlock():
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 2187
    row.numero_documento = None
    db = MagicMock()
    db.get.return_value = row

    attempts = {"n": 0}

    def execute_side_effect(*_a, **_k):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise OperationalError(
                "UPDATE cuotas",
                {},
                Exception("deadlock detected"),
            )
        return MagicMock()

    db.execute.side_effect = execute_side_effect

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={},
    ), patch(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
    ) as lock, patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": False},
    ), patch(
        "app.services.pago_numero_documento.liberar_serial_tras_baja_o_cambio",
    ), patch(
        "app.core.db_transient.time.sleep",
    ):
        result = ejecutar_eliminar_pago(db, 43300, current_user=None)

    assert result["ok"] is True
    assert attempts["n"] >= 2
    assert lock.call_count >= 2
    db.rollback.assert_called()
    db.commit.assert_called()


def test_ejecutar_eliminar_pago_agotados_deadlocks_devuelve_500():
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 2187
    row.numero_documento = None
    db = MagicMock()
    db.get.return_value = row

    def execute_side_effect(*_a, **_k):
        raise OperationalError(
            "UPDATE cuotas",
            {},
            Exception("deadlock detected"),
        )

    db.execute.side_effect = execute_side_effect

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={},
    ), patch(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
    ), patch(
        "app.core.db_transient.time.sleep",
    ):
        with pytest.raises(HTTPException) as exc_info:
            ejecutar_eliminar_pago(db, 43300, current_user=None)

    assert exc_info.value.status_code == 500
    assert "deadlock" in str(exc_info.value.detail).lower()
