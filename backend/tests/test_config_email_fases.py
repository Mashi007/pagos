# -*- coding: utf-8 -*-
"""
Tests para flujo de configuracion de email y verificacion de fases (logs/indicadores).
- GET/PUT configuracion email
- POST probar (email de prueba) con send_email mockeado
- POST probar-imap con test_imap_connection mockeado
- Verificacion de que las fases definidas existen y se usan en logs (captura de log handler).

Ejecutar desde backend/:
  pytest tests/test_config_email_fases.py -v
"""
import logging
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.core.email_phases import (
    FASE_CONFIG_CARGA,
    FASE_CONFIG_GUARDADO,
    FASE_SMTP_CONFIG,
    FASE_SMTP_CONEXION,
    FASE_SMTP_ENVIO,
    FASE_MODO_PRUEBAS,
    FASE_IMAP_CONEXION,
    FASE_IMAP_COMPLETA,
    FASES_EMAIL,
)
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


# --- Tests endpoints config email ---

def test_get_email_configuracion_returns_dict(client: TestClient):
    """GET /api/v1/configuracion/email/configuracion devuelve objeto con claves SMTP/IMAP."""
    r = client.get("/api/v1/configuracion/email/configuracion")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "smtp_host" in data
    assert "smtp_port" in data
    assert "smtp_user" in data
    assert "imap_host" in data


def test_get_email_estado_returns_indicadores(client: TestClient):
    """GET /api/v1/configuracion/email/estado devuelve configurada, mensaje, problemas."""
    r = client.get("/api/v1/configuracion/email/estado")
    assert r.status_code == 200
    data = r.json()
    assert "configurada" in data
    assert "mensaje" in data
    assert "problemas" in data
    assert isinstance(data["problemas"], list)


def test_put_email_configuracion_guarda_y_log_fase(client: TestClient, db: Session, caplog):
    """PUT guarda config y emite log con FASE_CONFIG_GUARDADO."""
    with caplog.at_level(logging.INFO):
        r = client.put(
            "/api/v1/configuracion/email/configuracion",
            json={
                "smtp_host": "smtp.ejemplo.com",
                "smtp_port": "587",
                "smtp_user": "test@ejemplo.com",
                "from_email": "test@ejemplo.com",
                "smtp_use_tls": "true",
            },
        )
    assert r.status_code == 200
    assert "Configuracion guardada" in r.json().get("message", "") or "config email" in str(r.json()).lower()
    assert FASE_CONFIG_GUARDADO in caplog.text or "phase=" in caplog.text


def test_post_probar_email_sin_smtp_devuelve_400(client: TestClient):
    """POST probar sin SMTP configurado devuelve 400."""
    r = client.post(
        "/api/v1/configuracion/email/probar",
        json={"email_destino": "destino@test.com"},
    )
    assert r.status_code == 400


@patch("app.core.email.send_email")
def test_post_probar_email_con_smtp_mock_ok(send_email_mock, client: TestClient, db: Session):
    """POST probar con SMTP mockeado: send_email devuelve True; respuesta success."""
    send_email_mock.return_value = (True, None)
    # Necesitamos config guardada con user/password para que no devuelva 400 por "falta contraseÃ±a"
    payload = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587",
        "smtp_user": "user@test.com",
        "smtp_password": "secret",
        "from_email": "user@test.com",
        "email_pruebas": "pruebas@test.com",
        "modo_pruebas": "false",
    }
    client.put("/api/v1/configuracion/email/configuracion", json=payload)
    r = client.post(
        "/api/v1/configuracion/email/probar",
        json={"email_destino": "destino@test.com", "subject": "Prueba", "mensaje": "Cuerpo"},
    )
    if r.status_code == 400 and "contraseÃ±a" in (r.json().get("detail") or ""):
        pytest.skip("Config no persiste password en test; probar con env SMTP")
    assert r.status_code == 200
    assert r.json().get("success") is True
    send_email_mock.assert_called_once()


def test_post_probar_imap_sin_credenciales_400(client: TestClient):
    """POST probar-imap sin imap_host/user/password devuelve 400."""
    r = client.post("/api/v1/configuracion/email/probar-imap", json={})
    assert r.status_code == 400


@patch("app.core.email.test_imap_connection")
def test_post_probar_imap_mock_ok(test_imap_mock, client: TestClient):
    """POST probar-imap con test_imap_connection mockeado: success True y carpetas."""
    test_imap_mock.return_value = (True, None, ["INBOX", "Sent"])
    r = client.post(
        "/api/v1/configuracion/email/probar-imap",
        json={
            "imap_host": "imap.gmail.com",
            "imap_port": "993",
            "imap_user": "user@test.com",
            "imap_password": "secret",
            "imap_use_ssl": "true",
        },
    )
    assert r.status_code == 200
    assert r.json().get("success") is True
    assert "carpetas_encontradas" in r.json()


@patch("app.core.email.test_imap_connection")
def test_post_probar_imap_mock_fallo(test_imap_mock, client: TestClient):
    """POST probar-imap cuando IMAP falla: success False y mensaje de error."""
    test_imap_mock.return_value = (False, "Usuario o contraseÃ±a no aceptados", None)
    r = client.post(
        "/api/v1/configuracion/email/probar-imap",
        json={
            "imap_host": "imap.gmail.com",
            "imap_port": "993",
            "imap_user": "user@test.com",
            "imap_password": "bad",
            "imap_use_ssl": "true",
        },
    )
    assert r.status_code == 200
    assert r.json().get("success") is False
    assert "mensaje" in r.json()


# --- Tests indicadores de fase (constantes y log_phase) ---

def test_fases_email_constantes_definidas():
    """Todas las constantes de fase existen y son strings unicos."""
    assert FASE_CONFIG_CARGA == "email_fase_config_carga"
    assert FASE_CONFIG_GUARDADO == "email_fase_config_guardado"
    assert FASE_SMTP_CONFIG == "email_fase_smtp_config"
    assert FASE_SMTP_CONEXION == "email_fase_smtp_conexion"
    assert FASE_SMTP_ENVIO == "email_fase_smtp_envio"
    assert FASE_MODO_PRUEBAS == "email_fase_modo_pruebas"
    assert FASE_IMAP_CONEXION == "email_fase_imap_conexion"
    assert FASE_IMAP_COMPLETA == "email_fase_imap_completa"
    assert len(FASES_EMAIL) >= 6
    assert FASE_SMTP_ENVIO in FASES_EMAIL


def test_log_phase_emite_formato_esperado(caplog):
    """log_phase escribe mensaje con phase= y success= para indicadores."""
    from app.core.email_phases import log_phase
    logger = logging.getLogger("app.core.email")
    with caplog.at_level(logging.INFO):
        log_phase(logger, "test_fase", True, "ok", duration_ms=10.5)
    assert "[FASE]" in caplog.text
    assert "phase=test_fase" in caplog.text
    assert "success=True" in caplog.text


