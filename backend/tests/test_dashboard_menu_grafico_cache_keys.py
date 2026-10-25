"""Contrato: wrappers cacheados y warm usan las mismas claves/params por defecto."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "app" / "api" / "v1" / "endpoints" / "dashboard"


def test_resumen_cobranzas_uses_menu_grafico_cached():
    src = (DASHBOARD / "graficos.py").read_text(encoding="utf-8")
    assert 'menu_grafico_cached(\n        "resumen-cobranzas-mensual"' in src
    assert 'fecha_inicio or "2025-02-01"' in src


def test_financiamiento_inicial_uses_menu_grafico_cached():
    src = (DASHBOARD / "financiamiento_inicial.py").read_text(encoding="utf-8")
    assert 'menu_grafico_cached(\n        "financiamiento-inicial"' in src
    assert "def _compute_financiamiento_dashboard_inicial(" in src


def test_warm_includes_resumen_and_financiamiento():
    src = (DASHBOARD / "__init__.py").read_text(encoding="utf-8")
    assert '"resumen-cobranzas-mensual"' in src
    assert '"financiamiento-inicial"' in src
    assert "get_opciones_filtros(db=db)" in src
    assert "_compute_resumen_cobranzas_mensual" in src
    assert "_compute_financiamiento_dashboard_inicial" in src
