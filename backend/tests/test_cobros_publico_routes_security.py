"""Regresiones de seguridad para endpoints publicos de Cobros."""
import os
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros_publico import routes


class _FakeUpload:
    filename = "comprobante.jpg"
    content_type = "image/jpeg"

    async def read(self) -> bytes:
        return bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46])


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _FakeExecuteResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return _FakeScalarResult(self._value)


class _FakeDb:
    def __init__(self, cliente):
        self._cliente = cliente
        self.commits = 0
        self.rollbacks = 0

    def execute(self, _stmt):
        return _FakeExecuteResult(self._cliente)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_enviar_reporte_publico_ignora_confirmacion_humana_tampered(monkeypatch):
    """Un cliente publico no puede convertir validadores fallidos en auto-aprobacion."""
    cliente = SimpleNamespace(id=123, nombres="Cliente Prueba", cedula="V12345678")
    pago_reportado = SimpleNamespace(
        id=456,
        estado="pendiente",
        gemini_coincide_exacto=None,
        gemini_comentario=None,
        falla_validadores_manual=None,
    )
    db = _FakeDb(cliente)
    import_called = False

    monkeypatch.setattr(routes, "get_client_ip", lambda _request: "127.0.0.1")
    monkeypatch.setattr(routes, "check_rate_limit_enviar_reporte", lambda _ip: None)
    monkeypatch.setattr(
        routes,
        "_cobros_public_otp_required",
        lambda _origen, _request: False,
    )
    monkeypatch.setattr(
        routes,
        "validate_cedula",
        lambda _cedula: {"valido": True, "valor_formateado": "V-12345678"},
    )
    monkeypatch.setattr(
        routes.cpr,
        "prestamos_aprobados_del_cliente",
        lambda _db, _cliente_id: [object()],
    )
    monkeypatch.setattr(
        routes.cpr,
        "error_si_no_puede_reportar_en_web",
        lambda _prestamos: None,
    )
    monkeypatch.setattr(
        routes.cpr,
        "normalizar_y_validar_campos_formulario",
        lambda **_kwargs: (None, SimpleNamespace(moneda_guardar="BS", observacion=None)),
    )
    monkeypatch.setattr(
        routes.cpr,
        "validar_reglas_bs_tasa_monto_fecha",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        routes.cpr,
        "mime_efectivo_comprobante_web",
        lambda *_args: "image/jpeg",
    )
    monkeypatch.setattr(
        routes.cpr,
        "validar_adjunto_comprobante_bytes",
        lambda *_args, **_kwargs: (None, "comprobante.jpg"),
    )
    monkeypatch.setattr(
        routes.cpr,
        "crear_pago_reportado_con_referencia_o_retry",
        lambda *_args, **_kwargs: (pago_reportado, "RPC-TEST", None),
    )
    monkeypatch.setattr(
        routes,
        "compare_form_with_image",
        lambda *_args, **_kwargs: {"coincide_exacto": False, "comentario": "No coincide"},
    )
    monkeypatch.setattr(
        routes,
        "reportado_falla_validadores_cobros",
        lambda _db, _pr: True,
    )

    def _fail_if_imported(*_args, **_kwargs):
        nonlocal import_called
        import_called = True
        raise AssertionError(
            "No debe importar automaticamente un reporte publico con validadores fallidos"
        )

    monkeypatch.setattr(
        routes.cpr,
        "intentar_importar_reportado_automatico",
        _fail_if_imported,
    )

    response = await routes.enviar_reporte_publico(
        request=SimpleNamespace(headers={}),
        background_tasks=BackgroundTasks(),
        db=db,
        tipo_cedula="V",
        numero_cedula="12345678",
        fecha_pago=date(2026, 5, 18),
        institucion_financiera="Banco",
        numero_operacion="OP123",
        monto=100.0,
        moneda="BS",
        comprobante=_FakeUpload(),
        observacion=None,
        contact_website=None,
        fuente_tasa_cambio="euro",
        confirmacion_humana="true",
    )

    assert response.ok is True
    assert response.estado_reportado == "en_revision"
    assert pago_reportado.gemini_coincide_exacto == "false"
    assert pago_reportado.gemini_comentario == "No coincide"
    assert pago_reportado.falla_validadores_manual is True
    assert import_called is False


def test_confirmacion_humana_operador_requiere_permiso_explicito():
    assert routes._confirmacion_humana_operador(
        "true",
        permitir_confirmacion_humana=False,
    ) is False
    assert routes._confirmacion_humana_operador(
        "true",
        permitir_confirmacion_humana=True,
    ) is True
