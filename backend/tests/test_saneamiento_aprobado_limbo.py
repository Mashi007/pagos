"""Tests del saneamiento de aprobado limbo (sin inventar datos)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.cobros.saneamiento_aprobado_limbo import (
    _puede_intentar_carga_automatica,
    asegurar_aprobado_no_queda_en_limbo,
    sanear_aprobados_en_limbo,
    sanear_en_revision_recuperables,
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


def test_sanear_en_revision_reintenta_bug_current_user():
    db = MagicMock()
    pr = _pr(
        estado="en_revision",
        gemini_comentario="[AUTOIMPORT] name 'current_user' is not defined",
        falla_validadores_manual=True,
    )
    db.execute.return_value.scalars.return_value.all.return_value = [1]
    db.get.return_value = pr
    with patch(
        "app.services.cobros.saneamiento_aprobado_limbo.pago_reportado_colisiona_tabla_pagos",
        return_value=False,
    ), patch(
        "app.services.cobros.saneamiento_aprobado_limbo.asegurar_aprobado_no_queda_en_limbo",
        return_value="importado",
    ) as aseg:
        res = sanear_en_revision_recuperables(
            db, max_ids=10, dry_run=False, include_detalle=True
        )
    assert res.scanned == 1
    assert res.reintentado_import == 1
    assert res.importado_auto == 1
    aseg.assert_called_once()


def test_reconciliar_gmail_cuotas_ok_enlaza_pago():
    from app.services.pagos_gmail.gmail_abcd_cuotas_traza import (
        reconciliar_cuotas_ok_sin_pago_id,
    )

    db = MagicMock()
    traza = SimpleNamespace(
        id=1,
        numero_referencia="DOC-9",
        pago_id=None,
        prestamo_id=None,
        pago_estado_final=None,
        detalle="",
    )
    pago = SimpleNamespace(
        id=99, prestamo_id=7, estado="aplicado", numero_documento="DOC-9"
    )
    exec1 = MagicMock()
    exec1.scalars.return_value.all.return_value = [traza]
    exec2 = MagicMock()
    exec2.scalar_one_or_none.return_value = pago
    db.execute.side_effect = [exec1, exec2]
    out = reconciliar_cuotas_ok_sin_pago_id(db, max_ids=10, dry_run=False)
    assert out["linked"] == 1
    assert traza.pago_id == 99
    assert traza.prestamo_id == 7
    db.commit.assert_called()


def test_serial_canonico_colision_ignora_sufijo_no_vecino():
    from app.services.cobros.pago_reportado_documento import (
        serial_comprobante_canonico_colision,
    )

    base = "740087401913898"
    vecino = "740087401913897"
    assert serial_comprobante_canonico_colision(base) == base
    assert serial_comprobante_canonico_colision(f"{base}_P7321") == base
    assert serial_comprobante_canonico_colision(f"{base} §CD:A3639") == base
    assert serial_comprobante_canonico_colision(vecino) != serial_comprobante_canonico_colision(
        base
    )


def test_sanear_importados_fantasma_demote_sin_inventar():
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(id=16320, estado="importado", referencia_interna="RPC-20260813-00084")
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [16320]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [id_exec, row_exec, []]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.scanned == 1
    assert res.a_en_revision == 1
    assert pr.estado == "en_revision"
    assert pr.falla_validadores_manual is True
    db.commit.assert_called()


def test_sanear_importados_fantasma_no_toca_si_ya_aplicado():
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(id=9, estado="importado")
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [9]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [id_exec, row_exec, [("12345678", None, None)]]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 0
    assert pr.estado == "importado"


def test_sanear_importados_rpc_en_cartera_no_cierra_limbo():
    """Un pago con documento = RPC-… no sustituye el serial del banco."""
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(
        id=16335,
        estado="importado",
        numero_operacion="740087404973233",
        referencia_interna="RPC-20260813-00099",
    )
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [16335]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [
        id_exec,
        row_exec,
        [("RPC-20260813-00099", "RPC-20260813-00099", None)],
    ]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 1
    assert pr.estado == "en_revision"


def test_sanear_importados_sin_operacion_va_a_revision():
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(
        id=16195,
        estado="importado",
        numero_operacion="",
        referencia_interna="RPC-20260812-00094",
    )
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [16195]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [id_exec, row_exec, []]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 1
    assert pr.estado == "en_revision"


def test_sanear_importados_pendiente_sin_cuota_va_a_revision():
    """Colisión con pago PENDIENTE sin cuota_pagos no debe dejar el reporte en limbo."""
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(id=14541, estado="importado", numero_operacion="445857312501006336")
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [14541]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [id_exec, row_exec, []]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 1
    assert pr.estado == "en_revision"
    assert pr.falla_validadores_manual is True


def test_sanear_importados_sufijo_cd_no_es_limbo():
    """Mismo serial con §CD: y cuota/PAGADO no se reabre."""
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(
        id=15817,
        estado="importado",
        numero_operacion="740087409575354",
        referencia_interna="RPC-20260810-00112",
    )
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [15817]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [
        id_exec,
        row_exec,
        [("740087409575354 §CD:A6079", None, None)],
    ]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 0
    assert pr.estado == "importado"


def test_sanear_en_revision_vacio_no_cierra_por_rpc():
    db = MagicMock()
    pr = _pr(
        id=15533,
        estado="en_revision",
        numero_operacion="",
        referencia_interna="RPC-20260807-00091",
        gemini_comentario="[AUTOIMPORT] name 'current_user' is not defined",
    )
    db.execute.return_value.scalars.return_value.all.return_value = [15533]
    db.get.return_value = pr
    with patch(
        "app.services.cobros.saneamiento_aprobado_limbo.pago_reportado_colisiona_tabla_pagos",
        return_value=True,
    ) as col:
        res = sanear_en_revision_recuperables(
            db, max_ids=10, dry_run=False, include_detalle=True
        )
    col.assert_not_called()
    assert res.marcado_importado_colision == 0
    assert pr.estado == "en_revision"


def test_sanear_importados_rev_manual_va_a_revision():
    """Marcador OCR REV-MANUAL no cierra el limbo aunque exista un pago con ese texto."""
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    pr = _pr(
        id=14115,
        estado="importado",
        numero_operacion="REV-MANUAL-ms3grar2-xckiyc",
        referencia_interna="RPC-20260727-00083",
    )
    id_exec = MagicMock()
    id_exec.scalars.return_value.all.return_value = [14115]
    row_exec = MagicMock()
    row_exec.scalars.return_value.all.return_value = [pr]
    db.execute.side_effect = [
        id_exec,
        row_exec,
        [("REV-MANUAL-ms3grar2-xckiyc", None, None)],
    ]
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=False, include_detalle=True
    )
    assert res.a_en_revision == 1
    assert pr.estado == "en_revision"
    assert pr.falla_validadores_manual is True


def test_sanear_importados_pagina_after_id():
    from app.services.cobros.saneamiento_aprobado_limbo import (
        sanear_importados_sin_cartera_aplicada,
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = []
    res = sanear_importados_sin_cartera_aplicada(
        db, max_ids=10, dry_run=True, after_id=1000, include_detalle=False
    )
    assert res.scanned == 0
    assert res.last_id == 0
