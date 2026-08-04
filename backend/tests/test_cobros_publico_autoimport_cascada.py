"""
Regresion: auto-import de cobros publico no debe falsa-conciliar en_revision
ni tragar ValueError de cascada (commits 6c32c42 / a83c5dde).
"""
from __future__ import annotations

import os
import sys
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/pagos-test-autoimport.db")
os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.cobros import cobros_publico_reporte_service as cpr


def _pr(**kwargs):
    base = dict(
        estado="en_revision",
        institucion_financiera="BNV",
        numero_operacion="12345678",
        monto=50.0,
        fecha_pago=date(2026, 8, 1),
        falla_validadores_manual=True,
        gemini_comentario="OCR dudoso",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _pago_creado():
    return SimpleNamespace(
        id=99,
        estado="PAGADO",
        conciliado=True,
        fecha_conciliacion="ts",
        verificado_concordancia="SI",
    )


class TestReportadoDatosCargables:
    def test_datos_reales_cargables(self):
        assert cpr.reportado_datos_cargables_a_cartera(_pr()) is True

    def test_marcador_ocr_no_cargable(self):
        assert (
            cpr.reportado_datos_cargables_a_cartera(
                _pr(
                    institucion_financiera="REVISION_MANUAL",
                    numero_operacion="REV-MANUAL-1",
                )
            )
            is False
        )


def _run_autoimport(pr, *, import_res, cascada_side_effect=None, cascada_return=(1, 0)):
    db = MagicMock()
    pago = import_res.get("pago")
    cascada = MagicMock(return_value=cascada_return)
    if cascada_side_effect is not None:
        cascada = MagicMock(side_effect=cascada_side_effect)
    marca = MagicMock()

    import app.api.v1.endpoints.pagos as pagos_pkg

    with patch.object(
        pagos_pkg, "importar_un_pago_reportado_a_pagos", return_value=import_res
    ), patch.object(
        pagos_pkg, "_aplicar_pago_a_cuotas_interno", cascada
    ), patch(
        "app.services.cobros.pago_reportado_documento.pago_reportado_colisiona_tabla_pagos",
        return_value=False,
    ), patch(
        "app.services.cobros.pago_reportado_documento.claves_documento_pago_para_reportado",
        return_value=set(),
    ), patch(
        "app.services.pago_autoconciliacion.marcar_pago_autoconciliado", marca
    ):
        res = cpr.intentar_importar_reportado_automatico(
            db, pr, "RPC-TEST", "COBROS_PUBLIC"
        )
    return db, pago, cascada, marca, res


class TestAutoImportEnRevisionSinCascada:
    def test_en_revision_cargable_no_cascada_ni_autoconcilia(self):
        pr = _pr(estado="en_revision")
        pago = _pago_creado()
        db, pago, cascada, marca, res = _run_autoimport(
            pr, import_res={"ok": True, "pago": pago}
        )

        assert res.pago_id == 99
        assert res.error is None
        cascada.assert_not_called()
        marca.assert_not_called()
        assert pago.estado == "PENDIENTE"
        assert pago.conciliado is False
        assert pago.fecha_conciliacion is None
        assert pago.verificado_concordancia == "NO"
        assert pr.estado == "importado"
        assert pr.falla_validadores_manual is True
        assert "pago_sin_cascada_pendiente_aplicar" in (pr.gemini_comentario or "")
        db.commit.assert_called()


class TestAutoImportAprobadoValueErrorNoFalsaConciliacion:
    def test_value_error_cascada_hace_rollback_sin_marcar_autoconciliado(self):
        pr = _pr(estado="aprobado", falla_validadores_manual=False)
        pago = _pago_creado()
        db, _pago, cascada, marca, res = _run_autoimport(
            pr,
            import_res={"ok": True, "pago": pago},
            cascada_side_effect=ValueError("Suma aplicada supera monto"),
        )

        assert res.pago_id is None
        assert res.error and "Suma aplicada" in res.error
        cascada.assert_called_once()
        marca.assert_not_called()
        assert db.rollback.called
