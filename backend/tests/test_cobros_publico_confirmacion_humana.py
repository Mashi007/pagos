# -*- coding: utf-8 -*-
"""Seguridad del formulario publico de reporte de pagos."""

import asyncio
import os
import sys
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import BackgroundTasks

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros_publico import routes


class _ExecuteResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value


class _Upload:
    filename = "comprobante.jpg"
    content_type = "image/jpeg"

    async def read(self):
        return b"\xff\xd8\xff\xe0test"


def test_confirmacion_humana_publica_no_omite_validadores(monkeypatch):
    cliente = SimpleNamespace(id=7, nombres="Cliente Demo", cedula="V12345678")
    pr = SimpleNamespace(
        id=55,
        estado=None,
        gemini_coincide_exacto=None,
        gemini_comentario=None,
        falla_validadores_manual=None,
    )
    db = MagicMock()
    db.execute.return_value = _ExecuteResult(cliente)

    async def _compare_form_with_image_async(*_args, **_kwargs):
        return {"coincide_exacto": False, "comentario": "no coincide"}

    validar_mock = MagicMock(return_value=True)
    importar_mock = MagicMock()

    monkeypatch.setattr(routes, "get_client_ip", lambda _request: "127.0.0.1")
    monkeypatch.setattr(routes, "check_rate_limit_enviar_reporte", lambda _ip: None)
    monkeypatch.setattr(
        routes,
        "validate_cedula",
        lambda _cedula: {"valido": True, "valor_formateado": "V12345678"},
    )
    monkeypatch.setattr(routes, "_cobros_public_otp_required", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(routes, "emails_destino_desde_objeto", lambda _cliente: [])
    monkeypatch.setattr(routes, "unir_destinatarios_log", lambda _emails: "")
    monkeypatch.setattr(routes, "compare_form_with_image_async", _compare_form_with_image_async)
    monkeypatch.setattr(routes, "reportado_falla_validadores_cobros", validar_mock)
    monkeypatch.setattr(routes.cpr, "prestamos_aprobados_del_cliente", lambda _db, _cid: [object()])
    monkeypatch.setattr(routes.cpr, "error_si_no_puede_reportar_en_web", lambda _prestamos: None)
    monkeypatch.setattr(
        routes.cpr,
        "normalizar_y_validar_campos_formulario",
        lambda **_kwargs: (
            None,
            SimpleNamespace(moneda_guardar="USD", moneda_upper="USD", observacion=""),
        ),
    )
    monkeypatch.setattr(
        routes.cpr,
        "validar_reglas_bs_tasa_monto_fecha",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        routes.cpr,
        "mime_efectivo_comprobante_web",
        lambda _content_type, _filename: "image/jpeg",
    )
    monkeypatch.setattr(
        routes.cpr,
        "preparar_adjunto_comprobante_para_vision",
        lambda content, _ctype, filename, **_kwargs: (None, content, filename, "image/jpeg"),
    )
    monkeypatch.setattr(
        routes.cpr,
        "crear_pago_reportado_con_referencia_o_retry",
        lambda *_args, **_kwargs: (pr, "REF-55", None),
    )
    monkeypatch.setattr(
        routes.cpr,
        "aplicar_revision_manual_por_monto_alto_en_reportado",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(routes.cpr, "intentar_importar_reportado_automatico", importar_mock)

    resp = asyncio.run(
        routes.enviar_reporte_publico(
            request=SimpleNamespace(),
            background_tasks=BackgroundTasks(),
            db=db,
            tipo_cedula="V",
            numero_cedula="12345678",
            fecha_pago=date(2026, 6, 1),
            institucion_financiera="Banco",
            numero_operacion="ABC123",
            monto=100,
            moneda="USD",
            comprobante=_Upload(),
            confirmacion_humana="true",
        )
    )

    assert resp.ok is True
    assert resp.estado_reportado == "en_revision"
    assert pr.gemini_coincide_exacto == "false"
    assert pr.falla_validadores_manual is True
    validar_mock.assert_called_once_with(db, pr)
    importar_mock.assert_not_called()
