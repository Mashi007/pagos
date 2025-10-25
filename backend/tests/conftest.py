"""
Fixtures de Testing
Configuración común para todas las pruebas
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os
from typing import Generator

from app.main import app
from app.db.session import get_db, Base
from app.core.config import get_settings
from app.models.user import User
from app.core.security import get_password_hash


# Configuración de base de datos de prueba
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para pruebas asíncronas"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Crear base de datos de prueba temporal"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Crear sesión de base de datos para pruebas"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_client(db_session):
    """Crear cliente de prueba FastAPI"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Crear usuario de prueba"""
    user = User(
        email="test@example.com",
        nombre="Test",
        apellido="User",
        hashed_password=get_password_hash("testpassword123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session):
    """Crear usuario administrador de prueba"""
    admin = User(
        email="admin@example.com",
        nombre="Admin",
        apellido="User",
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def auth_headers(test_client, test_user):
    """Crear headers de autenticación para pruebas"""
    response = test_client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers(test_client, test_admin_user):
    """Crear headers de autenticación para admin"""
    response = test_client.post(
        "/api/v1/auth/login",
        data={"username": test_admin_user.email, "password": "adminpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_cliente_data():
    """Datos de ejemplo para cliente"""
    return {
        "cedula": "V12345678",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "telefono": "+58412123456",
        "email": "juan.perez@example.com",
        "direccion": "Caracas, Venezuela",
        "fecha_nacimiento": "1990-01-01",
        "ocupacion": "Ingeniero",
        "modelo_vehiculo": "Toyota Corolla",
        "concesionario": "Concesionario Test",
        "analista": "Analista Test",
        "estado": "ACTIVO",
        "notas": "Cliente de prueba",
    }


@pytest.fixture(scope="function")
def sample_pago_data():
    """Datos de ejemplo para pago"""
    return {
        "cedula_cliente": "V12345678",
        "fecha_pago": "2025-01-01T10:00:00",
        "monto_pagado": 1000.00,
        "numero_documento": "DOC001",
        "documento_nombre": "Comprobante de pago",
        "documento_tipo": "PDF",
        "notas": "Pago de prueba",
    }


@pytest.fixture(scope="function")
def sample_prestamo_data():
    """Datos de ejemplo para préstamo"""
    return {
        "cliente_id": 1,
        "monto_total": 50000.00,
        "monto_financiado": 45000.00,
        "monto_inicial": 5000.00,
        "tasa_interes": 15.0,
        "numero_cuotas": 24,
        "monto_cuota": 2000.00,
        "fecha_aprobacion": "2025-01-01",
        "fecha_primer_vencimiento": "2025-02-01",
        "modalidad": "MENSUAL",
        "destino_credito": "Compra de vehículo",
        "observaciones": "Préstamo de prueba",
    }


# Configuración de entorno de prueba
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configurar entorno de prueba"""
    # Configurar variables de entorno para testing
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"

    yield

    # Limpiar variables de entorno después de las pruebas
    test_env_vars = ["ENVIRONMENT", "DEBUG", "LOG_LEVEL"]
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
