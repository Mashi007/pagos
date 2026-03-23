# -*- coding: utf-8 -*-
"""
Test de API HTTP: envio minimo de correo desde POST /notificaciones/plantillas/{id}/enviar
con send_email mockeado (sin SMTP real).

Ejecutar desde backend/:
  pytest tests/test_notificaciones_enviar_plantilla_http.py -v
"""
import os
import sys
import uuid
from datetime import date
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.plantilla_notificacion import PlantillaNotificacion
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


@pytest.fixture
def cliente_y_plantilla_envio_http(db: Session):
    """Cliente con email y plantilla activa; se eliminan al terminar el test."""
    cedula = f"VHTTP{uuid.uuid4().hex[:12]}"
    email_dest = f"pytest_envio_http_{uuid.uuid4().hex[:8]}@test.local"
    cliente = Cliente(
        cedula=cedula,
        nombres="Cliente API envio HTTP",
        telefono="04140000000",
        email=email_dest,
        direccion="Test",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="pytest",
        notas="test_notificaciones_enviar_plantilla_http",
    )
    plantilla = PlantillaNotificacion(
        nombre=f"Plantilla pytest HTTP {uuid.uuid4().hex[:6]}",
        tipo="PAGO_5_DIAS_ANTES",
        asunto="Asunto {{nombre}}",
        cuerpo="<p>Cuerpo {{cedula}}</p>",
        activa=True,
    )
    db.add(cliente)
    db.add(plantilla)
    db.commit()
    db.refresh(cliente)
    db.refresh(plantilla)
    yield cliente, plantilla
    try:
        db.delete(plantilla)
        db.delete(cliente)
        db.commit()
    except Exception:
        db.rollback()


@patch("app.core.email_config_holder.get_email_activo_servicio", return_value=True)
@patch("app.core.email.send_email", return_value=(True, None))
def test_post_plantillas_enviar_http_llama_send_email(
    mock_send_email,
    mock_activo,
    client: TestClient,
    cliente_y_plantilla_envio_http,
):
    """El endpoint HTTP ejecuta la misma ruta de codigo que produccion hasta send_email (mockeado)."""
    cliente, plantilla = cliente_y_plantilla_envio_http
    url = f"/api/v1/notificaciones/plantillas/{plantilla.id}/enviar"
    r = client.post(url, params={"cliente_id": cliente.id}, json={})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("message")
    assert data.get("destinatario") == cliente.email
    mock_activo.assert_called_with("notificaciones")
    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    assert args[0] == [cliente.email]
    assert "Asunto" in (args[1] or "")
    assert kwargs.get("servicio") == "notificaciones"
    assert kwargs.get("tipo_tab") == plantilla.tipo


@patch("app.core.email_config_holder.get_email_activo_servicio", return_value=True)
@patch("app.core.email.send_email", return_value=(False, "SMTP rechazado (test)"))
def test_post_plantillas_enviar_http_send_email_falla_502(
    mock_send_email,
    mock_activo,
    client: TestClient,
    cliente_y_plantilla_envio_http,
):
    cliente, plantilla = cliente_y_plantilla_envio_http
    r = client.post(
        f"/api/v1/notificaciones/plantillas/{plantilla.id}/enviar",
        params={"cliente_id": cliente.id},
        json={},
    )
    assert r.status_code == 502
    assert "SMTP" in (r.json().get("detail") or "")
    mock_send_email.assert_called_once()
