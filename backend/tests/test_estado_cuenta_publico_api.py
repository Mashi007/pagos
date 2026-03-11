# -*- coding: utf-8 -*-
"""
Tests de API para estado de cuenta público: solicitar-codigo y verificar-codigo.

Ejecutar desde backend/:
  pytest tests/test_estado_cuenta_publico_api.py -v
  python -m pytest tests/test_estado_cuenta_publico_api.py -v
"""
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.estado_cuenta_codigo import EstadoCuentaCodigo


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db: Session):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    from app.core.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def cliente_con_email(db: Session):
    """Cliente de prueba con email para recibir código."""
    cedula = f"V{datetime.now().strftime('%H%M%S')}01"
    c = Cliente(
        cedula=cedula,
        nombres="Cliente Test Estado Cuenta",
        telefono="04140000001",
        email="estado-cuenta-test@example.com",
        direccion="Calle Test",
        fecha_nacimiento=date(1985, 5, 15),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_solicitar_codigo_sin_cedula(client: TestClient):
    """POST solicitar-codigo sin cedula o con cedula vacía debe devolver error."""
    r = client.post(
        "/api/v1/estado-cuenta/public/solicitar-codigo",
        json={"cedula": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
    assert "cedula" in (data.get("error") or "").lower()


def test_solicitar_codigo_cedula_invalida(client: TestClient):
    """POST solicitar-codigo con cédula inválida debe devolver error."""
    r = client.post(
        "/api/v1/estado-cuenta/public/solicitar-codigo",
        json={"cedula": "INVALID"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False


def test_solicitar_codigo_cedula_no_registrada(client: TestClient):
    """POST solicitar-codigo con cédula válida pero no en BD devuelve ok con mensaje genérico."""
    r = client.post(
        "/api/v1/estado-cuenta/public/solicitar-codigo",
        json={"cedula": "V99999999"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "mensaje" in data


@patch("app.api.v1.endpoints.estado_cuenta_publico.send_email")
def test_solicitar_codigo_crea_codigo_y_responde_ok(
    mock_send_email,
    client: TestClient,
    db: Session,
    cliente_con_email: Cliente,
):
    """Con cliente con email, solicitar-codigo crea fila en estado_cuenta_codigos y responde ok."""
    cedula_norm = cliente_con_email.cedula.replace("-", "")

    r = client.post(
        "/api/v1/estado-cuenta/public/solicitar-codigo",
        json={"cedula": cliente_con_email.cedula},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True

    row = db.execute(
        select(EstadoCuentaCodigo)
        .where(EstadoCuentaCodigo.cedula_normalizada == cedula_norm)
        .order_by(EstadoCuentaCodigo.creado_en.desc())
    ).scalars().first()
    assert row is not None
    rec = row[0] if hasattr(row, "__getitem__") else row
    assert rec.codigo is not None
    assert len(rec.codigo) == 6
    assert rec.usado is False
    mock_send_email.assert_called_once()


@patch("app.api.v1.endpoints.estado_cuenta_publico.send_email")
def test_verificar_codigo_ok_devuelve_pdf_base64(
    mock_send_email,
    client: TestClient,
    db: Session,
    cliente_con_email: Cliente,
):
    """Verificar código correcto devuelve ok y pdf_base64."""
    cedula_norm = cliente_con_email.cedula.replace("-", "")
    now = datetime.utcnow()
    expira = now + timedelta(minutes=120)
    codigo_row = EstadoCuentaCodigo(
        cedula_normalizada=cedula_norm,
        email=cliente_con_email.email,
        codigo="123456",
        expira_en=expira.replace(tzinfo=None),
        usado=False,
        creado_en=now.replace(tzinfo=None),
    )
    db.add(codigo_row)
    db.commit()
    db.refresh(codigo_row)

    r = client.post(
        "/api/v1/estado-cuenta/public/verificar-codigo",
        json={"cedula": cliente_con_email.cedula, "codigo": "123456"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "pdf_base64" in data
    assert len(data["pdf_base64"]) > 0

    db.refresh(codigo_row)
    assert codigo_row.usado is True


def test_verificar_codigo_invalido(client: TestClient, db: Session, cliente_con_email: Cliente):
    """Verificar código incorrecto devuelve ok=False."""
    cedula_norm = cliente_con_email.cedula.replace("-", "")
    now = datetime.utcnow()
    codigo_row = EstadoCuentaCodigo(
        cedula_normalizada=cedula_norm,
        email=cliente_con_email.email,
        codigo="111111",
        expira_en=(now + timedelta(minutes=120)).replace(tzinfo=None),
        usado=False,
        creado_en=now.replace(tzinfo=None),
    )
    db.add(codigo_row)
    db.commit()

    r = client.post(
        "/api/v1/estado-cuenta/public/verificar-codigo",
        json={"cedula": cliente_con_email.cedula, "codigo": "999999"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
    assert "error" in data
