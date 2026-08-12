"""Tests del saneamiento de aprobado limbo (sin inventar datos)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.cobros.saneamiento_aprobado_limbo import (
    _puede_intentar_carga_automatica,
    asegurar_aprobado_no_queda_en_limbo,
    sanear_aprobados_en_limbo,
)


def _pr(**kwargs):
    base = dict(
        id=1,
        estado="aprobado",
        referencia_interna="RPC-20260301-00001",
        institucion_financiera="BNC",
        numero_operacion="12345678",
        monto=50.0,
        moneda="USD",
        fecha_pago=__import__("datetime").date(2026, 3, 1),
        gemini_comentario="",
        falla_validadores_manual=False,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_puede_intentar_carga_rechaza_marcador_ocr():
    pr = _pr(institucion_financiera="REVISION_MANUAL", numero_operacion="REV-MANUAL-1", monto=0.01)
    assert _puede_intentar_carga_automatica(pr) is False


def test_puede_intentar_carga_rechaza_umbral():
    pr = _pr(monto=600.0)
    assert _puede_intentar_carga_automatica(pr) is False


def test_puede_intentar_carga_ok_recibo_real():
    pr = _pr(monto=120.0)
    assert _puede_intentar_carga_automatica(pr) is True


def test_asegurar_demote_si_sigue_aprobado():
    db = MagicMock()
    pr = _pr()
    with patch(
        "app.services.cobros.saneamiento_aprobado_limbo.pago_reportado_colisiona_tabla_pagos",
        return_value=False,
    ), patch(
        "app.services.cobros.saneamiento_aprobado_limbo.intentar_importar_reportado_automatico",
        return_value=SimpleNamespace(error="omitido"),
    ):
        # Simula que el auto-import no cambió el estado.
        out = asegurar_aprobado_no_queda_en_limbo(db, pr, "RPC-1", "TEST")
    assert out == "en_revision"
    assert pr.estado == "en_revision"
    assert pr.falla_validadores_manual is True
    db.commit.assert_called()


def test_asegurar_importado_por_colision():
    db = MagicMock()
    pr = _pr()
    with patch(
        "app.services.cobros.saneamiento_aprobado_limbo.pago_reportado_colisiona_tabla_pagos",
        return_value=True,
    ):
        out = asegurar_aprobado_no_queda_en_limbo(db, pr, "RPC-1", "TEST")
    assert out == "importado"
    assert pr.estado == "importado"


def test_sanear_dry_run_colision_cuenta_sin_persistir_estado_si_mock():
    db = MagicMock()
    pr = _pr(id=9)
    db.execute.return_value.scalars.return_value.all.return_value = [9]
    db.get.return_value = pr
    with patch(
        "app.services.cobros.saneamiento_aprobado_limbo.pago_reportado_colisiona_tabla_pagos",
        return_value=True,
    ):
        res = sanear_aprobados_en_limbo(db, max_ids=10, dry_run=True, include_detalle=True)
    assert res.scanned == 1
    assert res.marcado_importado_colision == 1
    assert pr.estado == "aprobado"  # dry-run no muta
