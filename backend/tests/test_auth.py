# -*- coding: utf-8 -*-
"""
Tests de autenticación: login, refresh, me, 401 sin token.
Prioridad: asegurar que rutas protegidas exigen token y que login/refresh/me responden correctamente.

Ejecutar desde backend/:
  pytest tests/test_auth.py -v
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
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


# --- Auth status (público) ---

def test_auth_status_returns_configured_or_message(client: TestClient):
    """GET /api/v1/auth/status devuelve auth_configured y message."""
    r = client.get("/api/v1/auth/status")
    assert r.status_code == 200
    data = r.json()
    assert "auth_configured" in data
    assert "message" in data


# --- Login (con ADMIN_EMAIL y ADMIN_PASSWORD) ---

@patch("app.api.v1.endpoints.auth.settings")
def test_login_success_returns_tokens_and_user(patched_settings, client: TestClient, db: Session):
    """Login con credenciales correctas devuelve access_token, refresh_token y user."""
    patched_settings.ADMIN_EMAIL = "admin@example.com"
    patched_settings.ADMIN_PASSWORD = "admin123"
    patched_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    patched_settings.REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS = 30
    patched_settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS = 90
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123", "remember": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data.get("token_type") == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "admin@example.com"


@patch("app.api.v1.endpoints.auth.settings")
def test_login_invalid_password_returns_401(patched_settings, client: TestClient):
    """Login con contraseña incorrecta devuelve 401."""
    patched_settings.ADMIN_EMAIL = "admin@example.com"
    patched_settings.ADMIN_PASSWORD = "admin123"
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert "Credenciales" in (r.json().get("detail") or "")


# --- Me (requiere token) ---

def test_me_without_token_returns_401(client: TestClient):
    """GET /api/v1/auth/me sin Authorization devuelve 401."""
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


@patch("app.api.v1.endpoints.auth.settings")
def test_me_with_valid_token_returns_user(patched_settings, client: TestClient):
    """GET /api/v1/auth/me con Bearer válido devuelve el usuario."""
    patched_settings.ADMIN_EMAIL = "admin@example.com"
    patched_settings.ADMIN_PASSWORD = "admin123"
    patched_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    patched_settings.REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS = 30
    patched_settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS = 90
    login_r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login_r.status_code == 200, login_r.text
    token = login_r.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@example.com"


# --- Rutas protegidas exigen token ---

@pytest.fixture(scope="function")
def client_no_auth(db: Session):
    """Cliente sin override de get_current_user para probar 401."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_protected_route_without_token_returns_401(client_no_auth: TestClient):
    """Una ruta protegida sin token devuelve 401."""
    r = client_no_auth.get("/api/v1/configuracion/notificaciones/envios")
    assert r.status_code == 401


def test_protected_route_with_valid_token_succeeds(client: TestClient):
    """Con usuario inyectado (override), la ruta protegida responde 200."""
    r = client.get("/api/v1/configuracion/notificaciones/envios")
    assert r.status_code == 200
