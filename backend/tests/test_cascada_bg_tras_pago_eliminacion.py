# -*- coding: utf-8 -*-
"""Cascada BG tras PUT: no reset sync si hay DELETE de pago en el mismo préstamo."""
from unittest.mock import MagicMock, patch

from app.services.revision_manual_cascada_bg import (
    normalizar_respuesta_iniciar_cascada_bg,
)


def test_normalizar_eliminacion_en_proceso_es_requeue_ok():
    out = normalizar_respuesta_iniciar_cascada_bg(
        {
            "ok": False,
            "codigo": "eliminacion_en_proceso",
            "estado": {"token": "tok-del"},
            "requeue": True,
        }
    )
    assert out["ok"] is True
    assert out["token"] == "tok-del"


def test_normalizar_ya_activo_sigue_siendo_requeue_ok():
    out = normalizar_respuesta_iniciar_cascada_bg(
        {"ok": False, "codigo": "ya_activo", "estado": {"token": "tok-job"}}
    )
    assert out["ok"] is True
    assert out["token"] == "tok-job"


def test_normalizar_ok_passthrough():
    raw = {"ok": True, "token": "abc"}
    assert normalizar_respuesta_iniciar_cascada_bg(raw) == raw


def test_normalizar_error_real_no_se_disfraza():
    raw = {"ok": False, "codigo": "spawn_fail", "error": "no thread"}
    assert normalizar_respuesta_iniciar_cascada_bg(raw) == raw


def test_lanzar_cascada_bg_no_reset_sync_durante_eliminacion():
    """
    Trigger: DELETE de un pago (eliminacion_context) solapado con anular/editar
    otro pago del mismo préstamo. iniciar_cascada marca requeue y no spawnea;
    el fallback sync haría reset_y_reaplicar (DELETE all cuota_pagos) encima
    del DELETE aún abierto.
    """
    from app.api.v1.endpoints.pagos.crud_pagos_mutation_routes import (
        _lanzar_cascada_bg_tras_pago,
    )

    db = MagicMock()
    with patch(
        "app.services.revision_manual_cascada_bg.iniciar_cascada_revision_manual",
        return_value={
            "ok": False,
            "codigo": "eliminacion_en_proceso",
            "estado": {"token": "tok-del"},
            "requeue": True,
        },
    ), patch(
        "app.api.v1.endpoints.pagos.crud_pagos_mutation_routes._reaplicar_cascada_en_request",
    ) as sync:
        out = _lanzar_cascada_bg_tras_pago(
            db,
            prestamo_ids=[3202],
            pago_id=99,
            current_user=None,
        )
        sync.assert_not_called()
        assert out["cascada_en_proceso"] is True
        assert out["cascada_sincronizada"] is False
        assert out["cascada_bg_token"] == "tok-del"
