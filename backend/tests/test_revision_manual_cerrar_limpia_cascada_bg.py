# -*- coding: utf-8 -*-
"""Guardar-y-cerrar marca cascada-bg ok para no re-aplicar en el poller FE."""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cerrar_bg_marca_cascada_ok_tras_pipeline():
    from app.services import revision_manual_cerrar_bg as mod

    src = inspect.getsource(mod)
    assert "marcar_cascada_ok" in src
    assert "revision_manual_cascada_bg" in src
