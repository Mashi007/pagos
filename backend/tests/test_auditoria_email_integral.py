# -*- coding: utf-8 -*-
"""
Auditoría integral Auditoría Email — tests por sección.

Secciones:
  A) Query / filtros Gmail
  B) Bandeja (dict mensaje, NA cédula)
  C) Recibos / cola aprobación (dict, aprobar, revisión)
  D) Escaneo (defer, materializar, alineamiento)
  E) Modelo / schema / API surface
  F) Recibo → revisión manual → carga pagos_con_errores (cédula V6666666)
"""
from __future__ import annotations

import inspect
import os
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cédula de pruebas del sistema (cliente/sandbox).
CEDULA_PRUEBA = "V6666666"


# ---------------------------------------------------------------------------
# A) Query / filtros
# ---------------------------------------------------------------------------
class TestSeccionA_QueryFiltros:
    def test_por_defecto_incluye_etiquetados(self):
        from app.services.auditoria_email.query import (
            analizados_label_name,
            build_gmail_query,
        )

        q = build_gmail_query({"newerThanDays": 3})
        assert "in:inbox" in q
        assert f"-label:{analizados_label_name()}" not in q
        assert '-label:"' not in q

    def test_exclude_analizados_opcional(self):
        from app.services.auditoria_email.query import (
            analizados_label_name,
            build_gmail_query,
        )

        q = build_gmail_query({"newerThanDays": 3, "excludeAnalizados": True})
        assert f"-label:{analizados_label_name()}" in q

    def test_presets_catalogo_completo(self):
        from app.services.auditoria_email.query import PRESETS, criteria_from_preset

        for p in PRESETS:
            c = criteria_from_preset(p)
            assert c.get("preset") == p
            assert "newerThanDays" in c or "from" in c
            # Todos los presets productivos definen modo de adjunto (salvo fallback).
            assert "attachments" in c

    def test_comprobantes_ocr_pdf_or_image(self):
        from app.services.auditoria_email.query import criteria_from_preset

        assert criteria_from_preset("comprobantes-ocr")["attachments"] == "pdf_or_image"

    def test_lote_comprobantes_receipt_strong(self):
        from app.services.auditoria_email.query import criteria_from_preset

        c = criteria_from_preset("lote-comprobantes")
        assert c["attachments"] == "receipt_strong"
        assert c["newerThanDays"] == 30
        assert "subject" in c

    def test_webp_en_gmail_query(self):
        from app.services.auditoria_email.query import build_gmail_query

        q = build_gmail_query({"attachments": "pdf_or_image", "newerThanDays": 7})
        assert "filename:webp" in q

    def test_fechas_eliminan_newer_than(self):
        from app.services.auditoria_email.query import apply_preset, build_gmail_query

        c = apply_preset(
            {"preset": "ultimos-7", "newerThanDays": 7, "dateFrom": "2026-01-01"}
        )
        assert c.get("newerThanDays") is None
        q = build_gmail_query(c)
        assert "newer_than:" not in q
        assert "after:" in q

    def test_apply_preset_ultimos_incluye_attachments(self):
        from app.services.auditoria_email.query import apply_preset, build_gmail_query

        for p in ("ultimos-7", "ultimos-30"):
            c = apply_preset({"preset": p})
            assert c.get("attachments") == "pdf_or_image", p
            q = build_gmail_query({"preset": p})
            assert "has:attachment" in q
            assert "filename:webp" in q

    def test_batch_exige_cota_fecha(self):
        from app.services.auditoria_email.query import has_date_bound

        assert not has_date_bound({})
        assert has_date_bound({"newerThanDays": 1})
        assert has_date_bound({"dateTo": "2026-08-01"})

    def test_postfiltro_min_kb_requiere_payload(self):
        from app.services.auditoria_email.query import criteria_needs_payload_inspection

        assert criteria_needs_payload_inspection({"attachmentMinKb": 40})
        assert not criteria_needs_payload_inspection({"attachments": "pdf_only"})


# ---------------------------------------------------------------------------
# B) Bandeja
# ---------------------------------------------------------------------------
class TestSeccionB_Bandeja:
    def test_message_dict_cedula_na(self):
        from app.services.auditoria_email.scan_service import _message_dict

        msg = SimpleNamespace(
            id=1,
            scan_id=2,
            gmail_message_id="m1",
            gmail_thread_id="t1",
            source="gmail",
            from_email="cliente@mail.com",
            from_name="Cliente",
            subject="Pago",
            snippet="",
            internal_date=datetime(2026, 8, 28, 12, 0, 0),
            has_attachment=True,
            attachment_types=["a.pdf"],
            attachment_max_kb=100,
            extract_json={},
            classify="digitalizado",
            route="pendiente_aprobacion",
            sla_hours=None,
            riesgo=None,
            evidencia=None,
            ocr_json=None,
            pipelines_json=None,
            ingested_at=datetime(2026, 8, 28, 12, 5, 0),
        )
        d = _message_dict(msg)
        assert d["fromEmail"] == "cliente@mail.com"
        assert d["cedula"] is None
        assert d["cedulaLabel"] == "NA"
        assert d["attachmentCount"] == 1
        assert d["internalDate"]

    def test_message_dict_cedula_desde_extract(self):
        from app.services.auditoria_email.scan_service import _message_dict

        msg = SimpleNamespace(
            id=2,
            scan_id=2,
            gmail_message_id="m2",
            gmail_thread_id=None,
            source="gmail",
            from_email="x@y.com",
            from_name=None,
            subject="s",
            snippet=None,
            internal_date=None,
            has_attachment=False,
            attachment_types=[],
            attachment_max_kb=None,
            extract_json={"cedula": " V19208662 "},
            classify=None,
            route=None,
            sla_hours=None,
            riesgo=None,
            evidencia=None,
            ocr_json=None,
            pipelines_json=None,
            ingested_at=None,
        )
        d = _message_dict(msg)
        assert d["cedula"] == "V19208662"
        assert d["cedulaLabel"] == "V19208662"

    def test_list_messages_soporta_filtro_cedula_na(self):
        from app.services.auditoria_email import scan_service as svc

        src = inspect.getsource(svc.list_messages)
        assert "cedula_filter" in src
        assert 'cf_low in ("na"' in src or "sin_cedula" in src
        assert "cedulaLabel" in src


# ---------------------------------------------------------------------------
# C) Recibos / cola aprobación
# ---------------------------------------------------------------------------
def _fake_receipt(**kwargs):
    base = dict(
        id=10,
        message_id=5,
        gmail_message_id="gm-1",
        filename="comp.jpg",
        mime_type="image/jpeg",
        size_kb=50,
        cedula="V123",
        monto=25.5,
        banco="MERCANTIL",
        fecha_pago="28/08/2026",
        numero_referencia="REF001",
        image_url="/api/v1/pagos/comprobante-imagen/1",
        status="pending",
        sync_id=99,
        sync_item_id=100,
        gmail_temporal_id=7,
        pago_id=None,
        pago_error_id=None,
        last_error=None,
        route="pendiente_aprobacion",
        ocr_status="pagos_gmail",
        created_at=datetime(2026, 8, 28),
        resolved_at=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestSeccionC_RecibosAprobacion:
    def test_receipt_dict_campos_operativos(self):
        from app.services.auditoria_email.receipts_service import receipt_dict

        d = receipt_dict(_fake_receipt())
        assert d["cedula"] == "V123"
        assert d["banco"] == "MERCANTIL"
        assert d["fechaPago"] == "28/08/2026"
        assert d["serial"] == "REF001"
        assert d["imageUrl"]
        assert d["status"] == "pending"

    def test_aprobar_ya_approved_idempotente(self):
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _fake_receipt(status="approved", pago_id=55)
        db = MagicMock()
        db.get.return_value = row
        out = aprobar_recibo(db, 10)
        assert out["ok"] is True
        assert out.get("already") is True

    def test_aprobar_estado_revision_no_repite_alta(self):
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _fake_receipt(status="revision", pago_error_id=99)
        db = MagicMock()
        db.get.return_value = row
        with patch(
            "app.services.auditoria_email.receipts_service._enviar_a_pagos_con_errores"
        ) as mig, patch(
            "app.services.pagos_gmail.pago_abcd_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd"
        ) as abcd:
            out = aprobar_recibo(db, 10)
        assert out["ok"] is False
        assert out.get("already") is True
        assert "estado_no_pending" in str(out.get("motivo") or "")
        assert "revision" in str(out.get("redirect") or "")
        mig.assert_not_called()
        abcd.assert_not_called()

    def test_aprobar_banco_ef_deriva_revision(self):
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _fake_receipt(banco="BANCAMIGA", status="pending")
        db = MagicMock()
        db.get.return_value = row
        with patch(
            "app.services.auditoria_email.receipts_service._enviar_a_pagos_con_errores",
            return_value={
                "ok": False,
                "redirect": "/pagos?pestana=revision&revisar=1",
                "status": "revision",
                "motivo": "banco_solo_revision",
            },
        ) as mig:
            out = aprobar_recibo(db, 10)
            assert out["ok"] is False
            assert "revision" in str(out.get("redirect") or "")
            mig.assert_called_once()

    def test_aprobar_cuotas_ok(self):
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _fake_receipt(banco="MERCANTIL", status="pending")
        db = MagicMock()
        db.get.return_value = row
        ok_res = {"ok": True, "etapa_final": "CUOTAS_OK", "pago_id": 777}

        with patch(
            "app.services.pagos_gmail.pago_abcd_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd",
            return_value=ok_res,
        ):
            out = aprobar_recibo(db, 10)
        assert out["ok"] is True
        assert row.status == "approved"
        assert row.pago_id == 777

    def test_aprobar_falla_validadores_envia_revision(self):
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _fake_receipt(banco="BNC", status="pending")
        db = MagicMock()
        db.get.return_value = row
        fail = {"ok": False, "motivo": "sin_prestamo_aprobado_unico", "etapa_final": "OMITIDO"}

        with patch(
            "app.services.pagos_gmail.pago_abcd_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd",
            return_value=fail,
        ), patch(
            "app.services.auditoria_email.receipts_service._enviar_a_pagos_con_errores",
            return_value={
                "ok": False,
                "redirect": "/pagos?pestana=revision&revisar=1",
                "motivo": "sin_prestamo_aprobado_unico",
                "status": "revision",
            },
        ) as mig:
            out = aprobar_recibo(db, 10)
            assert out["ok"] is False
            mig.assert_called_once()

    def test_revision_manual_ok(self):
        from app.services.auditoria_email.receipts_service import revision_manual_recibo

        row = _fake_receipt()
        db = MagicMock()
        db.get.return_value = row
        with patch(
            "app.services.auditoria_email.receipts_service._enviar_a_pagos_con_errores",
            return_value={
                "ok": False,
                "redirect": "/pagos?pestana=revision&revisar=1",
                "status": "revision",
            },
        ):
            out = revision_manual_recibo(db, 10)
        assert out["ok"] is True


# ---------------------------------------------------------------------------
# D) Escaneo / defer / alineamiento
# ---------------------------------------------------------------------------
class TestSeccionD_Escaneo:
    def test_pipeline_acepta_defer_autoconciliacion(self):
        from app.services.pagos_gmail.pipeline import run_pipeline

        sig = inspect.signature(run_pipeline)
        assert "defer_autoconciliacion" in sig.parameters
        assert sig.parameters["defer_autoconciliacion"].default is False

    def test_run_pagos_pipeline_lot_pasa_defer_true(self):
        from app.services.auditoria_email import scan_service as svc

        src = inspect.getsource(svc._run_pagos_pipeline_lot)
        assert "defer_autoconciliacion=True" in src

    def test_post_pipeline_usa_cola_recibos_no_anti_limbo_alta(self):
        from app.services.auditoria_email import scan_service as svc

        src = inspect.getsource(svc._post_pipeline_cola_recibos)
        assert "materializar_recibos_desde_sync" in src
        assert "cerrar_lote_anti_limbo" not in src

    def test_manifest_y_alineamiento_cola_recibos(self):
        from app.services.auditoria_email.scan_service import MANIFEST_VERSION, alineamiento

        assert MANIFEST_VERSION.startswith("2.4")
        with patch(
            "app.core.database.SessionLocal",
            side_effect=RuntimeError("sin-bd-en-test"),
        ):
            al = alineamiento()
        assert al["manifest_version"] == MANIFEST_VERSION
        ids = {c["id"] for c in al["checks"]}
        assert "cola_recibos_aprobacion" in ids
        assert "bandeja_minima" in ids
        assert "recibos_thumb_auth" in ids
        assert any(
            "Aprobar" in f or "Recibos" in f or "digitalizar" in f for f in al["flujo"]
        )

    def test_scheduler_auto_advance_registrable(self):
        from app.core import scheduler as sch

        assert hasattr(sch, "AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID")
        assert hasattr(sch, "_job_auditoria_email_auto_advance")
        src = inspect.getsource(sch._job_auditoria_email_auto_advance)
        assert "AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED" in src

    def test_auto_advance_rescata_running_huerfano(self):
        """Un job running sin latido debe entrar al auto-avance a los 10 min,
        no a los 45: si no, queda «En curso» sin worker casi una hora."""
        from app.services.auditoria_email import scan_service as svc

        src = inspect.getsource(svc.auto_advance_paused_scans)
        assert "_scan_looks_orphaned_running" in src


# ---------------------------------------------------------------------------
# D2) Ciclo de vida del hilo de escaneo (running fantasma)
# ---------------------------------------------------------------------------
def _scan_falso(scan_id: int, status: str = "paused") -> SimpleNamespace:
    ahora = datetime.utcnow()
    return SimpleNamespace(
        id=scan_id,
        mode="batch",
        status=status,
        source="gmail",
        criteria_json={},
        pipeline_ids_json=["pagos_gmail.vigente"],
        lot_size=50,
        max_messages=100,
        gmail_query="in:inbox",
        page_token=None,
        processed_total=0,
        listed_total=0,
        rejected_total=0,
        lots_done=0,
        last_error=None,
        created_by="test@test",
        created_at=ahora,
        updated_at=ahora,
        finished_at=None,
    )


class _DbFalsa:
    def __init__(self, scan):
        self._scan = scan
        self.commits = 0

    def get(self, _model, _pk):
        return self._scan

    def add(self, _obj):
        pass

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        pass


class TestSeccionD2_HiloEscaneo:
    def test_candado_tomado_no_deja_running_sin_worker(self):
        """Regresión: advance_scan marcaba running y solo después el hilo
        intentaba el candado. Si estaba tomado, el hilo salía y el escaneo
        quedaba running en BD sin nadie trabajando."""
        from app.services.auditoria_email import scan_service as svc

        scan = _scan_falso(90_001)
        db = _DbFalsa(scan)
        lock = svc._advance_lock_for(90_001)
        assert lock.acquire(blocking=False)
        try:
            with patch.object(svc, "assert_ready_for_scan", return_value={}):
                out = svc.advance_scan(db, 90_001)
        finally:
            lock.release()

        assert out.get("alreadyRunning") is True
        assert scan.status == "paused"
        assert db.commits == 0

    def test_hilo_recibe_el_candado_ya_tomado(self):
        """El candado debe viajar al hilo: si lo tomara el hilo por su cuenta
        reaparece la ventana en la que el escaneo queda running huérfano."""
        from app.services.auditoria_email import scan_service as svc

        scan = _scan_falso(90_002)
        db = _DbFalsa(scan)
        lock = svc._advance_lock_for(90_002)
        lanzados = {}

        class _HiloFalso:
            def __init__(self, target=None, args=(), **kwargs):
                lanzados["target"] = target
                lanzados["args"] = args

            def start(self):
                lanzados["started"] = True

        with patch.object(svc, "assert_ready_for_scan", return_value={}), patch.object(
            svc.threading, "Thread", _HiloFalso
        ):
            svc.advance_scan(db, 90_002)

        assert lanzados.get("started") is True
        assert lanzados["args"][2] is lock
        assert lanzados["target"] is svc._advance_gmail_background
        # El hilo simulado nunca corrió, así que el candado sigue tomado:
        # advance_scan no debe soltarlo al ceder la propiedad.
        assert lock.locked()
        lock.release()

    def test_lote_fallido_a_media_faena_sigue_reanudable(self):
        """El auto-reanudar de la UI exige scan.paused. Un lote que murió con
        progreso > 0 y sin cursor salía como no reanudable y el escaneo pasaba
        a depender solo del scheduler (5 min por corrida)."""
        from app.services.auditoria_email import scan_service as svc

        scan = _scan_falso(90_003, status="paused")
        scan.processed_total = 7
        scan.lots_done = 0
        scan.page_token = None
        assert svc._scan_dict(scan)["paused"] is True

    def test_scan_agotado_no_se_marca_reanudable(self):
        from app.services.auditoria_email import scan_service as svc

        scan = _scan_falso(90_004, status="paused")
        scan.processed_total = scan.max_messages
        assert svc._scan_dict(scan)["paused"] is False

    def test_keepalive_gunicorn_conoce_el_escaneo(self):
        """Sin esta sonda el arbiter mata el worker a mitad de un lote de OCR."""
        import pathlib

        from app.services.auditoria_email import scan_service as svc

        assert svc.hay_escaneos_email_activos() in (True, False)
        conf = (
            pathlib.Path(__file__).resolve().parents[1] / "gunicorn.conf.py"
        ).read_text(encoding="utf-8")
        assert "hay_escaneos_email_activos" in conf
        assert "app.services.auditoria_email.scan_service" in conf


# ---------------------------------------------------------------------------
# E) Modelo / schema / API
# ---------------------------------------------------------------------------
class TestSeccionE_ModeloApi:
    def test_receipt_model_tiene_columnas_cola(self):
        from app.models.auditoria_email import AuditoriaEmailReceipt

        cols = {c.name for c in AuditoriaEmailReceipt.__table__.columns}
        for needed in (
            "banco",
            "fecha_pago",
            "numero_referencia",
            "image_url",
            "status",
            "sync_id",
            "pago_id",
            "pago_error_id",
            "last_error",
            "resolved_at",
        ):
            assert needed in cols, needed

    def test_schema_startup_idempotente_sin_tabla(self):
        from app.core.auditoria_email_schema_startup import ensure_auditoria_email_schema

        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        # fetchone None → tabla no existe → return temprano
        conn.execute.return_value.fetchone.return_value = None
        ensure_auditoria_email_schema(engine)

    def test_api_routes_registradas(self):
        from app.api.v1.endpoints.auditoria import email_routes as er

        paths = sorted(
            {
                getattr(r, "path", None)
                for r in er.router.routes
                if getattr(r, "path", None)
            }
        )
        needed = [
            "/email/status",
            "/email/scans",
            "/email/scans/preset-defaults",
            "/email/bandeja",
            "/email/recibos",
            "/email/recibos/{receipt_id}/aprobar",
            "/email/recibos/{receipt_id}/revision-manual",
            "/email/alineamiento",
        ]
        for p in needed:
            assert p in paths, f"falta ruta {p} en {paths}"

    def test_as_float_helper(self):
        from app.services.auditoria_email.receipts_service import _as_float

        assert _as_float("25.5") == 25.5
        assert _as_float("25,5") == 25.5
        assert _as_float(None) is None
        assert _as_float("abc") is None

    def test_frontend_service_contrato_surface(self):
        """Contrato UI↔API: métodos críticos presentes en el cliente TS."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "frontend",
            "src",
            "services",
            "auditoriaEmailService.ts",
        )
        assert os.path.isfile(path), path
        text = open(path, encoding="utf-8").read()
        for needle in (
            "presetDefaults",
            "bandeja",
            "cedula",
            "aprobarRecibo",
            "revisionManualRecibo",
            "/recibos/${id}/aprobar",
            "/recibos/${id}/revision-manual",
        ):
            assert needle in text, needle

    def test_ui_bandeja_y_recibos_tienen_acciones(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bandeja = open(
            os.path.join(
                root, "frontend", "src", "pages", "auditoriaEmail", "AuditoriaEmailBandejaPage.tsx"
            ),
            encoding="utf-8",
        ).read()
        recibos = open(
            os.path.join(
                root, "frontend", "src", "pages", "auditoriaEmail", "AuditoriaEmailRecibosPage.tsx"
            ),
            encoding="utf-8",
        ).read()
        assert "cedulaMode" in bandeja and "NA" in bandeja
        assert "ComprobanteThumb" in recibos
        assert "aprobarRecibo" in recibos and "aprobarRecibosLote" in recibos
        # El recibo que no pasa validadores no se manda a revisión con una
        # llamada aparte: Aprobar devuelve el destino y la UI navega allí.
        assert "redirectRevision" in recibos
        assert "res.redirect" in recibos


# ---------------------------------------------------------------------------
# F) Recibo → revisión manual → carga en pagos_con_errores (V6666666)
# ---------------------------------------------------------------------------
def _recibo_v666(**kwargs):
    base = dict(
        id=9001,
        message_id=501,
        gmail_message_id="gm-v666-test",
        filename="comp_v666.jpg",
        mime_type="image/jpeg",
        size_kb=80,
        cedula=CEDULA_PRUEBA,
        monto=12.5,
        banco="MERCANTIL",
        fecha_pago="28/08/2026",
        numero_referencia="REFV666TEST001",
        image_url="/api/v1/pagos/comprobante-imagen/abcdef0123456789abcdef0123456789",
        status="pending",
        sync_id=77,
        sync_item_id=88,
        gmail_temporal_id=None,
        pago_id=None,
        pago_error_id=None,
        last_error=None,
        route="pendiente_aprobacion",
        ocr_status="pagos_gmail",
        created_at=datetime(2026, 8, 28),
        resolved_at=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _db_mock_para_alta_pago_error(row):
    """Session mínima: captura PagoConError en add() y asigna id en flush()."""
    from app.models.pago_con_error import PagoConError

    db = MagicMock()
    db.get.return_value = row
    captured: dict = {"pago_error": None}

    def _add(obj):
        if isinstance(obj, PagoConError):
            captured["pago_error"] = obj
        return None

    def _flush():
        pe = captured["pago_error"]
        if pe is not None and getattr(pe, "id", None) is None:
            pe.id = 555001

    empty = MagicMock()
    empty.scalars.return_value.first.return_value = None
    empty.scalars.return_value.all.return_value = []
    db.execute.return_value = empty
    db.add.side_effect = _add
    db.flush.side_effect = _flush
    return db, captured


class TestSeccionF_ReciboARevisionYCargaPagos:
    """
    Paso operativo: Recibos → Revisión manual / Aprobar fallido
    → alta en pagos_con_errores con cédula de pruebas V6666666.
    """

    def test_formatear_cedula_prueba_estable(self):
        from app.services.pagos_gmail.helpers import formatear_cedula

        assert formatear_cedula(CEDULA_PRUEBA) == CEDULA_PRUEBA
        assert formatear_cedula("6666666") == CEDULA_PRUEBA
        assert formatear_cedula("V-06666666") == CEDULA_PRUEBA

    def test_enviar_a_pagos_crea_fila_con_v6666666(self):
        from app.services.auditoria_email.receipts_service import (
            _enviar_a_pagos_con_errores,
        )

        row = _recibo_v666()
        db, captured = _db_mock_para_alta_pago_error(row)

        with patch(
            "app.api.v1.endpoints.pagos_gmail.routes._migrar_pendientes_gmail_a_con_errores_core",
            return_value={"migrados": 0},
        ), patch(
            "app.services.pago_numero_documento.numero_documento_ya_registrado",
            return_value=False,
        ):
            out = _enviar_a_pagos_con_errores(
                db, row, motivo="test_carga_v666_revision"
            )

        pe = captured["pago_error"]
        assert pe is not None, "Debió crear PagoConError desde el recibo"
        assert pe.cedula_cliente == CEDULA_PRUEBA
        assert pe.usuario_registro == "AUDITORIA_EMAIL"
        assert pe.estado == "PENDIENTE"
        assert pe.conciliado is False
        assert pe.institucion_bancaria == "MERCANTIL"
        assert float(pe.monto_pagado) == 12.5
        # normalize_documento recorta letras del serial (REFV666TEST001 → dígitos).
        assert pe.numero_documento
        assert pe.referencia_pago
        assert "666" in str(pe.referencia_pago)
        assert "test_carga_v666_revision" in str(pe.observaciones or "")
        assert out["ok"] is False
        assert out["status"] == "revision"
        assert "pestana=revision" in str(out.get("redirect") or "")
        assert row.status == "revision"
        assert row.pago_error_id == 555001
        assert out.get("creado_desde_recibo") is True or (
            (out.get("migracion") or {}).get("creado_desde_recibo") is True
        )

    def test_revision_manual_v666_carga_pagos_con_errores(self):
        from app.services.auditoria_email.receipts_service import revision_manual_recibo

        row = _recibo_v666(id=9002, numero_referencia="REFV666REV002")
        db, captured = _db_mock_para_alta_pago_error(row)

        with patch(
            "app.api.v1.endpoints.pagos_gmail.routes._migrar_pendientes_gmail_a_con_errores_core",
            return_value={"migrados": 0},
        ), patch(
            "app.services.pago_numero_documento.numero_documento_ya_registrado",
            return_value=False,
        ):
            out = revision_manual_recibo(db, 9002)

        assert out["ok"] is True  # botón explícito marca ok tras enviar
        assert out["status"] == "revision"
        assert "pestana=revision" in str(out.get("redirect") or "")
        pe = captured["pago_error"]
        assert pe is not None
        assert pe.cedula_cliente == CEDULA_PRUEBA
        assert "revision_manual_usuario" in str(pe.observaciones or "")
        assert row.cedula == CEDULA_PRUEBA

    def test_aprobar_falla_validadores_v666_carga_pagos(self):
        """Aprobar con validadores en falso → misma puerta a pagos_con_errores."""
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _recibo_v666(
            id=9003,
            banco="BNC",
            numero_referencia="REFV666APR003",
        )
        db, captured = _db_mock_para_alta_pago_error(row)
        fail = {
            "ok": False,
            "motivo": "sin_prestamo_aprobado_unico",
            "etapa_final": "OMITIDO",
        }

        with patch(
            "app.services.pagos_gmail.pago_abcd_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd",
            return_value=fail,
        ), patch(
            "app.api.v1.endpoints.pagos_gmail.routes._migrar_pendientes_gmail_a_con_errores_core",
            return_value={"migrados": 0},
        ), patch(
            "app.services.pago_numero_documento.numero_documento_ya_registrado",
            return_value=False,
        ):
            out = aprobar_recibo(db, 9003)

        assert out["ok"] is False
        assert out.get("motivo") == "sin_prestamo_aprobado_unico"
        assert "pestana=revision" in str(out.get("redirect") or "")
        pe = captured["pago_error"]
        assert pe is not None
        assert pe.cedula_cliente == CEDULA_PRUEBA
        assert row.status == "revision"
        assert row.pago_error_id == 555001

    def test_aprobar_banco_ef_v666_sin_auto_alta(self):
        """E/F (BANCAMIGA) con V6666666 → revisión, no alta A–D."""
        from app.services.auditoria_email.receipts_service import aprobar_recibo

        row = _recibo_v666(
            id=9004,
            banco="BANCAMIGA",
            numero_referencia="REFV666EF004",
        )
        db, captured = _db_mock_para_alta_pago_error(row)

        with patch(
            "app.api.v1.endpoints.pagos_gmail.routes._migrar_pendientes_gmail_a_con_errores_core",
            return_value={"migrados": 0},
        ), patch(
            "app.services.pago_numero_documento.numero_documento_ya_registrado",
            return_value=False,
        ):
            out = aprobar_recibo(db, 9004)

        assert out["ok"] is False
        assert out["status"] == "revision"
        pe = captured["pago_error"]
        assert pe is not None
        assert pe.cedula_cliente == CEDULA_PRUEBA
        assert pe.institucion_bancaria == "BANCAMIGA"
        assert "banco_solo_revision" in str(pe.observaciones or "")
