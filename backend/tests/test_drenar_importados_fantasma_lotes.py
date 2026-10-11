"""Tests helper drenar_importados_fantasma_en_lotes (sin BD)."""
from unittest.mock import MagicMock

from app.services.cobros.saneamiento_aprobado_limbo import (
    SaneamientoImportadoFantasmaResultado,
    drenar_importados_fantasma_en_lotes,
)


def test_drenar_cero_loops_no_op():
    open_session = MagicMock()
    res = drenar_importados_fantasma_en_lotes(open_session, max_loops=0)
    assert res["loops"] == 0
    assert res["scanned"] == 0
    open_session.assert_not_called()


def test_drenar_para_en_cola_vacia(monkeypatch):
    calls = {"n": 0}

    def fake_sanear(*_a, **_k):
        calls["n"] += 1
        return SaneamientoImportadoFantasmaResultado(scanned=0, a_en_revision=0)

    monkeypatch.setattr(
        "app.services.cobros.saneamiento_aprobado_limbo.sanear_importados_sin_cartera_aplicada",
        fake_sanear,
    )
    db = MagicMock()
    res = drenar_importados_fantasma_en_lotes(lambda: db, max_loops=5, max_ids=100)
    assert res["loops"] == 1
    assert calls["n"] == 1
