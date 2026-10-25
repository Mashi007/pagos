# -*- coding: utf-8 -*-
"""Drain limbo al startup: loops acotados; sin Gmail/purge en el hilo post-deploy."""
from pathlib import Path


def test_cobros_limbo_startup_max_loops_default_and_bounds():
    from app.core.config import Settings

    field = Settings.model_fields["COBROS_LIMBO_STARTUP_MAX_LOOPS"]
    assert field.default == 1
    meta = field.metadata or []
    ge = next((m.ge for m in meta if getattr(m, "ge", None) is not None), None)
    le = next((m.le for m in meta if getattr(m, "le", None) is not None), None)
    assert ge == 0
    assert le == 2


def test_main_startup_drain_omits_gmail_and_purge_and_uses_limbo_env():
    main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    src = main_path.read_text(encoding="utf-8")
    # Localizar solo el cuerpo del drain de startup (entre def y el Thread que lo lanza).
    start = src.find("def _drain_aprobado_limbo_startup()")
    assert start >= 0
    end = src.find('name="sanear-aprobado-limbo-startup"', start)
    assert end > start
    block = src[start:end]
    assert "COBROS_LIMBO_STARTUP_MAX_LOOPS" in block
    assert "sanear_aprobados_en_limbo" in block
    assert "drenar_importados_fantasma_en_lotes" in block
    assert "reconciliar_cuotas_ok_sin_pago_id" not in block
    assert "purgar_borradores_huerfanos_antiguos" not in block
    # Tope de loops ya no es el hardcode 20.
    assert "range(20)" not in block
    assert "range(limbo_loops)" in block
