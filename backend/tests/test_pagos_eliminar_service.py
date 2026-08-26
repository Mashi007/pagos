# -*- coding: utf-8 -*-
"""Tests eliminación de pagos (coordination + servicio)."""
import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

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


def test_eliminar_con_reset_inicia_cascada_fuera_del_mutex():
    """DELETE no debe llamar iniciar_cascada mientras eliminacion_activa."""
    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    row = MagicMock()
    row.prestamo_id = 3202
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
        "app.services.pagos_cuotas_reaplicacion.realinear_cuotas_prestamo_desde_cuota_pagos",
        return_value={"ok": True, "requiere_reset_cascada": True},
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
    assert not eliminacion_activa(3202)


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


def test_normalizar_eliminacion_en_proceso_no_es_fallback_sync():
    from app.services.revision_manual_cascada_bg import (
        normalizar_resultado_iniciar_cascada,
    )

    out = normalizar_resultado_iniciar_cascada(
        {
            "ok": False,
            "codigo": "eliminacion_en_proceso",
            "requeue": True,
            "estado": {"token": "t-del"},
        }
    )
    assert out["ok"] is True
    assert out["token"] == "t-del"
