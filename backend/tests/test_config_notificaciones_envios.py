# -*- coding: utf-8 -*-
"""
Tests para el guardado de configuración de notificaciones/envíos (GET/PUT notificaciones/envios)
y para el respeto de los flags incluir_pdf_anexo e incluir_adjuntos_fijos en el envío.

Ejecutar desde backend/:
  pytest tests/test_config_notificaciones_envios.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.configuracion import Configuracion
from app.schemas.auth import UserResponse


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _fake_user():
    return UserResponse(
        id=1,
        email="test@test.local",
        nombre="Test",
        apellido="User",
        cargo="Tester",
        rol="administrador",
        is_active=True,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        last_login="2025-01-01T00:00:00Z",
    )


@pytest.fixture(scope="function")
def client(db: Session):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# --- Tests guardado de config (GET/PUT notificaciones/envios) ---

def test_get_notificaciones_envios_vacio_devuelve_dict(client: TestClient):
    """GET sin config previa devuelve {}."""
    r = client.get("/api/v1/configuracion/notificaciones/envios")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


def test_put_notificaciones_envios_guarda_y_get_devuelve_igual(client: TestClient, db: Session):
    """PUT guarda la config en BD; GET devuelve lo guardado (con tipos y claves globales)."""
    payload = {
        "modo_pruebas": True,
        "email_pruebas": "pruebas@test.local",
        "COBRANZA": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": True,
            "incluir_adjuntos_fijos": False,
            "cco": ["cc@test.local"],
        },
        "PAGO_5_DIAS_ANTES": {
            "habilitado": False,
            "plantilla_id": None,
            "incluir_pdf_anexo": None,
            "incluir_adjuntos_fijos": None,
        },
    }
    r = client.put("/api/v1/configuracion/notificaciones/envios", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body.get("message") is not None
    assert body.get("configuracion") == payload

    r2 = client.get("/api/v1/configuracion/notificaciones/envios")
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("modo_pruebas") is True
    assert data.get("email_pruebas") == "pruebas@test.local"
    assert data.get("COBRANZA", {}).get("incluir_pdf_anexo") is True
    assert data.get("COBRANZA", {}).get("incluir_adjuntos_fijos") is False
    assert data.get("PAGO_5_DIAS_ANTES", {}).get("habilitado") is False


def test_put_notificaciones_envios_cuerpo_no_dict_422(client: TestClient):
    """PUT con cuerpo que no es objeto JSON devuelve 422."""
    r = client.put("/api/v1/configuracion/notificaciones/envios", json=["array"])
    assert r.status_code == 422


# --- Tests respeto de flags en el envío (incluir_pdf_anexo, incluir_adjuntos_fijos) ---

@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_envio_cobranza_respeta_incluir_pdf_anexo_false(
    mock_sync,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    db: Session,
):
    """Con incluir_pdf_anexo=False no se llama a generar_carta_cobranza_pdf ni se adjunta PDF."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_send_email.return_value = (True, None)
    mock_adjunto_fijo.return_value = None

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "contexto_cobranza": {"prestamo_id": 1, "cliente_id": 1},
        }
    ]
    config_envios = {
        "modo_pruebas": False,
        "COBRANZA": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": False,
            "incluir_adjuntos_fijos": False,
        },
    }

    def get_tipo(_item):
        return "COBRANZA"

    with patch(
        "app.api.v1.endpoints.notificaciones_tabs.get_plantilla_asunto_cuerpo",
        return_value=("Asunto", "<p>Cuerpo</p>"),
    ):
        plantilla = MagicMock()
        plantilla.tipo = "COBRANZA"
        original_get = db.get

        def fake_db_get(model, pk):
            if getattr(model, "__name__", "") == "PlantillaNotificacion" and pk == 1:
                return plantilla
            return original_get(model, pk)

        with patch.object(db, "get", side_effect=fake_db_get):
            _enviar_correos_items(
                items,
                    "Asunto",
                    "Cuerpo",
                    config_envios,
                    get_tipo,
                    db,
                )

    mock_pdf.assert_not_called()
    mock_send_email.assert_called_once()
    call_kw = mock_send_email.call_args[1]
    assert call_kw.get("attachments") is None


@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_envio_cobranza_respeta_incluir_adjuntos_fijos_false(
    mock_sync,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    db: Session,
):
    """Con incluir_adjuntos_fijos=False no se llama a get_adjunto_fijo_cobranza_bytes para adjunto fijo."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_send_email.return_value = (True, None)
    mock_pdf.return_value = b"fake-pdf"

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "contexto_cobranza": {"prestamo_id": 1, "cliente_id": 1},
        }
    ]
    config_envios = {
        "modo_pruebas": False,
        "COBRANZA": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": True,
            "incluir_adjuntos_fijos": False,
        },
    }

    def get_tipo(_item):
        return "COBRANZA"

    with patch(
        "app.api.v1.endpoints.notificaciones_tabs.get_plantilla_asunto_cuerpo",
        return_value=("Asunto", "<p>Cuerpo</p>"),
    ):
        plantilla = MagicMock()
        plantilla.tipo = "COBRANZA"
        with patch.object(db, "get", return_value=plantilla):
            _enviar_correos_items(
                items,
                "Asunto",
                "Cuerpo",
                config_envios,
                get_tipo,
                db,
            )

    mock_adjunto_fijo.assert_not_called()
    mock_send_email.assert_called_once()
    call_kw = mock_send_email.call_args[1]
    attachments = call_kw.get("attachments")
    assert attachments is not None
    names = [a[0] if isinstance(a, tuple) else getattr(a, "filename", "") for a in attachments]
    assert "Carta_Cobranza.pdf" in names
    assert not any("adjunto" in n.lower() or "fijo" in n.lower() for n in names)


@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_envio_cobranza_con_ambos_flags_true_adjunta_pdf_y_fijo(
    mock_sync,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    db: Session,
):
    """Con incluir_pdf_anexo e incluir_adjuntos_fijos True se adjuntan PDF y adjunto fijo."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_send_email.return_value = (True, None)
    mock_pdf.return_value = b"fake-pdf-bytes"
    mock_adjunto_fijo.return_value = ("Documento.pdf", b"fake-adjunto")

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "contexto_cobranza": {"prestamo_id": 1, "cliente_id": 1},
        }
    ]
    config_envios = {
        "modo_pruebas": False,
        "COBRANZA": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": True,
            "incluir_adjuntos_fijos": True,
        },
    }

    def get_tipo(_item):
        return "COBRANZA"

    with patch(
        "app.api.v1.endpoints.notificaciones_tabs.get_plantilla_asunto_cuerpo",
        return_value=("Asunto", "<p>Cuerpo</p>"),
    ):
        plantilla = MagicMock()
        plantilla.tipo = "COBRANZA"
        with patch.object(db, "get", return_value=plantilla):
            _enviar_correos_items(
                items,
                "Asunto",
                "Cuerpo",
                config_envios,
                get_tipo,
                db,
            )

    mock_pdf.assert_called_once()
    mock_adjunto_fijo.assert_called_once()
    mock_send_email.assert_called_once()
    call_kw = mock_send_email.call_args[1]
    attachments = call_kw.get("attachments")
    assert attachments is not None
    assert len(attachments) >= 2
    names = [a[0] for a in attachments if isinstance(a, tuple)]
    assert "Carta_Cobranza.pdf" in names
    assert "Documento.pdf" in names
