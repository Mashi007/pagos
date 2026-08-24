# -*- coding: utf-8 -*-
"""Estado de cuenta incluye titulares aunque hayan recibido otras notificaciones de mora."""
from __future__ import annotations

import importlib


def test_estado_cuenta_sin_exclusion_por_mora_previa():
    mod = importlib.import_module("app.services.estado_cuenta_notificacion_envio")
    assert not hasattr(mod, "_sets_excluidos_por_mora_previa")
    assert not hasattr(mod, "_item_excluido_por_mora_previa")
    assert not hasattr(mod, "_TABS_EXCLUYEN_ESTADO_CUENTA")
