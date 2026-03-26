# -*- coding: utf-8 -*-
"""
Tests para historial de notificaciones por cédula y comprobante de envío.
Indicadores: GET historial-por-cedula, GET historial-por-cedula/excel, GET historial-por-cedula/{id}/comprobante-pdf.

Ejecutar desde backend/:
  pytest tests/test_notificaciones_historial.py -v
"""
import os
import sys
import uuid
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.envio_notificacion import EnvioNotificacion
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


@pytest.fixture(scope="function")
def un_envio_en_bd(db: Session):
    """Crea un registro en envios_notificacion para pruebas (cédula única por ejecución)."""
    cedula_unica = "V9" + uuid.uuid4().hex[:8].upper()
    envio = EnvioNotificacion(
        fecha_envio=datetime.utcnow(),
        tipo_tab="dias_5",
        asunto="Recordatorio cuota - Test",
        email="cliente@test.local",
        nombre="Cliente Test",
        cedula=cedula_unica,
        exito=True,
        error_mensaje=None,
        prestamo_id=1,
        correlativo=1,
    )
    db.add(envio)
    db.commit()
    db.refresh(envio)
    yield envio
    try:
        db.delete(envio)
        db.commit()
    except Exception:
        db.rollback()


# --- Historial por cédula ---


def test_historial_por_cedula_sin_cedula_422(client: TestClient):
    """GET historial-por-cedula sin cedula devuelve 422."""
    r = client.get("/api/v1/notificaciones/historial-por-cedula")
    assert r.status_code == 422


def test_historial_por_cedula_cedula_vacia_devuelve_vacio(client: TestClient):
    """GET con cedula vacía o solo espacios devuelve items vacíos (o 422 según validación)."""
    r = client.get("/api/v1/notificaciones/historial-por-cedula", params={"cedula": "   "})
    # Puede ser 422 (min_length=1) o 200 con items=[]
    if r.status_code == 200:
        data = r.json()
        assert data.get("items") == []
        assert data.get("total") == 0
    else:
        assert r.status_code == 422


def test_historial_por_cedula_sin_registros_devuelve_lista_vacia(client: TestClient):
    """GET con cédula que no tiene envíos devuelve items=[], total=0."""
    r = client.get("/api/v1/notificaciones/historial-por-cedula", params={"cedula": "V99999999"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("items") == []
    assert data.get("total") == 0
    assert "cedula" in data


def test_historial_por_cedula_con_registro(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET con cédula que tiene un envío devuelve ese registro."""
    cedula = un_envio_en_bd.cedula
    r = client.get("/api/v1/notificaciones/historial-por-cedula", params={"cedula": cedula})
    assert r.status_code == 200
    data = r.json()
    assert data.get("total") == 1
    assert len(data.get("items", [])) == 1
    item = data["items"][0]
    assert item.get("cedula") == cedula
    assert item.get("email") == "cliente@test.local"
    assert item.get("tipo_tab") == "dias_5"
    assert item.get("asunto") == "Recordatorio cuota - Test"
    assert item.get("exito") is True
    assert item.get("adjuntos") == []
    assert item.get("tiene_mensaje_html") is False
    assert item.get("tiene_mensaje_pdf") is False
    assert item.get("tiene_comprobante_pdf") is False


def test_historial_por_cedula_normaliza_cedula(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET con cédula con espacios/guiones encuentra el mismo registro (normalización)."""
    raw = un_envio_en_bd.cedula
    spaced = f"{raw[0]}-{raw[1:5]} {raw[5:]}" if len(raw) > 5 else raw
    r = client.get("/api/v1/notificaciones/historial-por-cedula", params={"cedula": spaced})
    assert r.status_code == 200
    data = r.json()
    assert data.get("total") >= 1
    assert any(it.get("cedula") == un_envio_en_bd.cedula for it in data.get("items", []))


# --- Excel historial ---


def test_historial_excel_descarga(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET historial-por-cedula/excel devuelve Excel con Content-Disposition."""
    r = client.get(
        "/api/v1/notificaciones/historial-por-cedula/excel",
        params={"cedula": un_envio_en_bd.cedula},
    )
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "") or "excel" in r.headers.get("content-type", "").lower()
    assert "attachment" in r.headers.get("content-disposition", "").lower() or "filename=" in r.headers.get("content-disposition", "")
    assert len(r.content) > 0


def test_historial_excel_sin_cedula_422(client: TestClient):
    """GET historial-por-cedula/excel sin cedula devuelve 422."""
    r = client.get("/api/v1/notificaciones/historial-por-cedula/excel")
    assert r.status_code == 422


# --- Comprobante por id ---


def test_comprobante_envio_redirige_a_pdf(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET .../comprobante redirige al PDF oficial."""
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/comprobante",
        follow_redirects=False,
    )
    assert r.status_code == 307
    loc = r.headers.get("location") or ""
    assert "comprobante-pdf" in loc


def test_comprobante_pdf_ok(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET .../comprobante-pdf devuelve PDF (generado al vuelo si no hay snapshot)."""
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/comprobante-pdf"
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_comprobante_envio_404(client: TestClient):
    """GET comprobante con id inexistente devuelve 404."""
    r = client.get("/api/v1/notificaciones/historial-por-cedula/99999999/comprobante")
    assert r.status_code == 404


# --- Cuerpo del mensaje (PDF) ---


def test_mensaje_html_sin_cuerpo_404(client: TestClient, un_envio_en_bd: EnvioNotificacion):
    """GET .../mensaje-html sin snapshot de cuerpo devuelve 404."""
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/mensaje-html",
        follow_redirects=False,
    )
    assert r.status_code == 404


def test_mensaje_html_redirige_a_pdf(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET .../mensaje-html redirige al PDF oficial cuando hay cuerpo."""
    un_envio_en_bd.mensaje_html = "<p>Prueba cuerpo</p>"
    db.commit()
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/mensaje-html",
        follow_redirects=False,
    )
    assert r.status_code == 307
    loc = r.headers.get("location") or ""
    assert "mensaje-pdf" in loc


def test_mensaje_pdf_ok(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET .../mensaje-pdf devuelve PDF cuando hay HTML guardado."""
    un_envio_en_bd.mensaje_html = "<table><tr><td>Uno</td><td>Dos</td></tr></table>"
    db.commit()
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/mensaje-pdf"
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_mensaje_pdf_solo_texto_ok(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """GET .../mensaje-pdf con solo mensaje_texto genera PDF."""
    un_envio_en_bd.mensaje_html = None
    un_envio_en_bd.mensaje_texto = "Linea 1\nLinea 2"
    db.commit()
    r = client.get(
        f"/api/v1/notificaciones/historial-por-cedula/{un_envio_en_bd.id}/mensaje-pdf"
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_historial_indica_tiene_mensaje_pdf(client: TestClient, db: Session, un_envio_en_bd: EnvioNotificacion):
    """El listado marca tiene_mensaje_pdf cuando hay HTML o texto."""
    un_envio_en_bd.mensaje_html = "<p>x</p>"
    db.commit()
    r = client.get(
        "/api/v1/notificaciones/historial-por-cedula",
        params={"cedula": un_envio_en_bd.cedula},
    )
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item.get("tiene_mensaje_pdf") is True
    assert item.get("tiene_mensaje_html") is True
