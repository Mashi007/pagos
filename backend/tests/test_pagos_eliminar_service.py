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


def test_eliminar_con_reset_inicia_cascada_fuera_del_mutex():
    """DELETE no debe llamar iniciar_cascada mientras eliminacion_activa."""
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 3202
    row.numero_documento = None
    db = MagicMock()
    db.get.return_value = row
    called = {}

    def fake_iniciar(*_a, **kwargs):
        called["activa"] = eliminacion_activa(3202)
        called["forzar"] = kwargs.get("forzar_spawn")
        return {"ok": True, "token": "tok-reset"}

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={"en_proceso": False},
    ), patch(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
    ), patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": True},
    ), patch(
        "app.services.pago_numero_documento.liberar_serial_tras_baja_o_cambio",
    ), patch(
        "app.services.revision_manual_cascada_bg.iniciar_cascada_revision_manual",
        side_effect=fake_iniciar,
    ):
        result = ejecutar_eliminar_pago(db, 95521, current_user=None)

    assert called.get("activa") is False
    assert called.get("forzar") is True
    assert result["ok"] is True
    assert result["cascada_en_proceso"] is True
    assert result["cascada_bg_token"] == "tok-reset"
    assert "requiere_reset_cascada" not in result
    assert not eliminacion_activa(3202)


def test_eliminar_requeue_concurrente_tambien_arranca_cascada():
    """Un guardado durante el DELETE deja requeue; hay que spawnear al salir."""
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 3202
    row.numero_documento = None
    db = MagicMock()
    db.get.return_value = row
    called = {}

    def fake_iniciar(*_a, **kwargs):
        called["forzar"] = kwargs.get("forzar_spawn")
        called["activa"] = eliminacion_activa(3202)
        return {"ok": True, "token": "tok-rq"}

    with patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={"en_proceso": True, "requeue": True, "token": "old"},
    ), patch(
        "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo",
    ), patch(
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": False},
    ), patch(
        "app.services.pago_numero_documento.liberar_serial_tras_baja_o_cambio",
    ), patch(
        "app.services.revision_manual_cascada_bg.iniciar_cascada_revision_manual",
        side_effect=fake_iniciar,
    ):
        result = ejecutar_eliminar_pago(db, 95522, current_user=None)

    assert called.get("activa") is False
    assert called.get("forzar") is True
    assert result["cascada_bg_token"] == "tok-rq"
    assert result["cascada_en_proceso"] is True


def test_iniciar_forzar_spawn_rompe_lock_fantasma():
    from app.services.revision_manual_cascada_bg import iniciar_cascada_revision_manual

    db = MagicMock()
    with patch(
        "app.services.pagos_eliminar_coordinacion.eliminacion_activa",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={"en_proceso": True, "requeue": True, "token": "old"},
    ), patch(
        "app.services.revision_manual_cascada_bg.marcar_requeue_cascada",
    ) as requeue, patch(
        "app.services.revision_manual_cascada_bg.mark_en_proceso",
    ), patch(
        "app.services.revision_manual_cascada_bg.spawn_cascada_bg",
        return_value=True,
    ) as spawn, patch(
        "app.services.revision_manual_cascada_bg.new_token",
        return_value="newtok",
    ):
        r = iniciar_cascada_revision_manual(
            db,
            prestamo_id=3202,
            prestamo_ids=[3202],
            pago_id=None,
            current_user=None,
            forzar_spawn=True,
        )
    assert r["ok"] is True
    assert r["token"] == "newtok"
    spawn.assert_called_once()
    requeue.assert_not_called()


def test_iniciar_sin_forzar_no_spawnea_si_en_proceso():
    from app.services.revision_manual_cascada_bg import iniciar_cascada_revision_manual

    db = MagicMock()
    with patch(
        "app.services.pagos_eliminar_coordinacion.eliminacion_activa",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.job_activo",
        return_value=False,
    ), patch(
        "app.services.revision_manual_cascada_bg.get_status",
        return_value={"en_proceso": True, "requeue": True, "token": "old"},
    ), patch(
        "app.services.revision_manual_cascada_bg.marcar_requeue_cascada",
    ) as requeue, patch(
        "app.services.revision_manual_cascada_bg.spawn_cascada_bg",
        return_value=True,
    ) as spawn:
        r = iniciar_cascada_revision_manual(
            db,
            prestamo_id=3202,
            prestamo_ids=[3202],
            pago_id=99,
            current_user=None,
        )
    assert r["ok"] is False
    assert r["codigo"] == "ya_activo"
    spawn.assert_not_called()
    requeue.assert_called_once()
