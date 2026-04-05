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


def test_merge_notificaciones_envios_put_parcial_no_elimina_otros_tipos():
    """Un cuerpo PUT parcial solo debe anadir o fusionar claves; no borrar casos omitidos."""
    from app.services.notificaciones_envios_store import merge_notificaciones_envios

    existing = {
        "modo_pruebas": False,
        "COBRANZA": {"habilitado": True, "plantilla_id": 1, "cco": ["a@test.local"]},
        "PAGO_5_DIAS_ANTES": {"habilitado": False, "plantilla_id": None},
    }
    incoming = {"PREJUDICIAL": {"habilitado": True, "plantilla_id": None}}
    out = merge_notificaciones_envios(existing, incoming)
    assert out["COBRANZA"]["plantilla_id"] == 1
    assert out["COBRANZA"]["cco"] == ["a@test.local"]
    assert out["PAGO_5_DIAS_ANTES"]["habilitado"] is False
    assert out["PREJUDICIAL"]["habilitado"] is True


def test_merge_notificaciones_envios_fila_dict_fusiona_campos():
    """Dentro de un mismo tipo, solo se actualizan las claves enviadas."""
    from app.services.notificaciones_envios_store import merge_notificaciones_envios

    existing = {"COBRANZA": {"habilitado": True, "plantilla_id": 1, "cco": ["x@test.local"]}}
    incoming = {"COBRANZA": {"plantilla_id": 2}}
    out = merge_notificaciones_envios(existing, incoming)
    assert out["COBRANZA"]["habilitado"] is True
    assert out["COBRANZA"]["plantilla_id"] == 2
    assert out["COBRANZA"]["cco"] == ["x@test.local"]


def test_put_notificaciones_envios_merge_parcial_conserva_tipos_previos(client: TestClient, db: Session):
    """Tras PUT completo y luego PUT solo con otro tipo, GET conserva ambos."""
    first = {
        "modo_pruebas": False,
        "COBRANZA": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": True,
            "incluir_adjuntos_fijos": False,
            "cco": [],
        },
        "PAGO_5_DIAS_ANTES": {
            "habilitado": False,
            "plantilla_id": None,
            "incluir_pdf_anexo": None,
            "incluir_adjuntos_fijos": None,
        },
    }
    r1 = client.put("/api/v1/configuracion/notificaciones/envios", json=first)
    assert r1.status_code == 200

    second = {
        "PREJUDICIAL": {
            "habilitado": True,
            "plantilla_id": None,
            "incluir_pdf_anexo": None,
            "incluir_adjuntos_fijos": None,
            "cco": [],
        },
    }
    r2 = client.put("/api/v1/configuracion/notificaciones/envios", json=second)
    assert r2.status_code == 200
    merged = r2.json().get("configuracion") or {}
    assert merged.get("COBRANZA", {}).get("plantilla_id") == 1
    assert merged.get("PAGO_5_DIAS_ANTES", {}).get("habilitado") is False
    assert merged.get("PREJUDICIAL", {}).get("habilitado") is True

    r3 = client.get("/api/v1/configuracion/notificaciones/envios")
    assert r3.status_code == 200
    data = r3.json()
    assert data.get("COBRANZA", {}).get("plantilla_id") == 1
    assert data.get("PAGO_5_DIAS_ANTES", {}).get("habilitado") is False
    assert data.get("PREJUDICIAL", {}).get("habilitado") is True


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


def test_put_notificaciones_envios_modo_pruebas_email_invalido_422(client: TestClient):
    """En modo pruebas, email_pruebas debe tener formato valido."""
    r = client.put(
        "/api/v1/configuracion/notificaciones/envios",
        json={"modo_pruebas": True, "email_pruebas": "sin_arroba"},
    )
    assert r.status_code == 422
    assert "email_pruebas" in (r.json().get("detail") or "").lower()


def test_put_notificaciones_envios_modo_pruebas_sin_email_422(client: TestClient):
    """En modo pruebas, email_pruebas no puede quedar vacio."""
    r = client.put(
        "/api/v1/configuracion/notificaciones/envios",
        json={"modo_pruebas": True, "email_pruebas": "   "},
    )
    assert r.status_code == 422


def test_put_notificaciones_envios_emails_pruebas_item_invalido_422(client: TestClient):
    """Lista emails_pruebas: cada entrada no vacia debe ser email valido."""
    r = client.put(
        "/api/v1/configuracion/notificaciones/envios",
        json={
            "modo_pruebas": True,
            "email_pruebas": "ok@test.local",
            "emails_pruebas": ["mal@@"],
        },
    )
    assert r.status_code == 422
    assert "emails_pruebas" in (r.json().get("detail") or "")


def test_get_envio_batch_ultimo_sin_ejecucion(client: TestClient, db: Session):
    """GET ultimo batch sin fila de resumen devuelve ultimo null."""
    from app.models.configuracion import Configuracion
    from app.services.notificaciones_envio_batch_resumen import CLAVE_ULTIMO_ENVIO_BATCH

    row = db.get(Configuracion, CLAVE_ULTIMO_ENVIO_BATCH)
    if row:
        db.delete(row)
        db.commit()
    r = client.get("/api/v1/notificaciones/envio-batch/ultimo")
    assert r.status_code == 200
    assert r.json().get("ultimo") is None


def test_get_envio_batch_ultimo_tras_persist(client: TestClient, db: Session):
    """Tras persistir resumen, GET devuelve el JSON guardado."""
    from app.services.notificaciones_envio_batch_resumen import persist_ultimo_envio_batch

    persist_ultimo_envio_batch(
        db,
        resultado={"enviados": 2, "fallidos": 1, "sin_email": 0},
        origen="test_pytest",
    )
    db.commit()
    r = client.get("/api/v1/notificaciones/envio-batch/ultimo")
    assert r.status_code == 200
    u = r.json().get("ultimo")
    assert u is not None
    assert u.get("enviados") == 2
    assert u.get("fallidos") == 1
    assert u.get("origen") == "test_pytest"


def test_fecha_cuota_a_texto_es():
    from datetime import date

    from app.services.notificacion_service import fecha_cuota_a_texto_es

    t = fecha_cuota_a_texto_es(date(2026, 4, 5))
    assert "abril" in t and "2026" in t


def test_format_item_texto_plantilla_incluye_fecha_vencimiento_display():
    from app.api.v1.endpoints.notificaciones import _format_item_texto_plantilla_por_defecto

    s = "Hola {nombre}, vence el {fecha_vencimiento_display}."
    item = {"nombre": "Ana", "fecha_vencimiento_display": "5 de abril de 2026"}
    assert (
        _format_item_texto_plantilla_por_defecto(s, item)
        == "Hola Ana, vence el 5 de abril de 2026."
    )


def test_sustituir_variables_fecha_vencimiento_display():
    from app.api.v1.endpoints.notificaciones import _sustituir_variables

    t = "Vence {{fecha_vencimiento_display}}"
    item = {
        "nombre": "X",
        "fecha_vencimiento": "2026-04-10",
        "fecha_vencimiento_display": "10 de abril de 2026",
    }
    assert _sustituir_variables(t, item) == "Vence 10 de abril de 2026"


def test_validar_notificaciones_envios_payload_modo_false_sin_emails_ok():
    from app.api.v1.endpoints.email_config_validacion import validar_notificaciones_envios_payload

    ok, errs = validar_notificaciones_envios_payload({"modo_pruebas": False})
    assert ok is True
    assert errs == []


def test_adjuntos_cumplen_paquete_requiere_cabecera_pdf():
    from app.api.v1.endpoints.notificaciones_tabs import _adjuntos_cumplen_paquete_completo

    ok, mot = _adjuntos_cumplen_paquete_completo(
        [("Carta_Cobranza.pdf", b"not-a-pdf"), ("Fijo.pdf", b"%PDF-1.4 x")]
    )
    assert ok is False
    assert "invalido" in mot or "variable" in mot


def test_adjuntos_cumplen_paquete_segundo_adjunto_no_pdf_no_invalida_paquete():
    """Solo se valida Carta_Cobranza.pdf; adjuntos extra corruptos no bloquean (compat sin volumen persistente)."""
    from app.api.v1.endpoints.notificaciones_tabs import _adjuntos_cumplen_paquete_completo

    ok, mot = _adjuntos_cumplen_paquete_completo(
        [("Carta_Cobranza.pdf", b"%PDF-1.4 carta"), ("Fijo.bin", b"XXXX")]
    )
    assert ok is True
    assert mot == ""


def test_contexto_cobranza_aplica_a_prestamo():
    from app.api.v1.endpoints.notificaciones import contexto_cobranza_aplica_a_prestamo

    assert contexto_cobranza_aplica_a_prestamo({"PRESTAMOS.ID": 5}, 5) is True
    assert contexto_cobranza_aplica_a_prestamo({"IDPRESTAMO": 5}, 5) is True
    assert contexto_cobranza_aplica_a_prestamo({"prestamo_id": 5}, 5) is True
    assert contexto_cobranza_aplica_a_prestamo({"PRESTAMOS.ID": 1}, 5) is False
    assert contexto_cobranza_aplica_a_prestamo({}, 5) is False
    assert contexto_cobranza_aplica_a_prestamo({"PRESTAMOS.ID": 5}, None) is False


def test_adjuntos_cumplen_paquete_dos_pdfs_validos_ok():
    from app.api.v1.endpoints.notificaciones_tabs import _adjuntos_cumplen_paquete_completo

    ok, mot = _adjuntos_cumplen_paquete_completo(
        [("Carta_Cobranza.pdf", b"%PDF-1.4 a"), ("Fijo.pdf", b"%PDF-1.4 b")]
    )
    assert ok is True
    assert mot == ""


# --- Tests respeto de flags en el envío (incluir_pdf_anexo, incluir_adjuntos_fijos) ---


def test_cfg_incluir_pdf_anexo_sin_clave_en_dict_es_true():
    from app.api.v1.endpoints.notificaciones_tabs import _cfg_incluir_pdf_anexo

    assert _cfg_incluir_pdf_anexo({}) is True
    assert _cfg_incluir_pdf_anexo({"habilitado": True}) is True
    assert _cfg_incluir_pdf_anexo({"incluir_pdf_anexo": False}) is False
    assert _cfg_incluir_pdf_anexo({"incluir_pdf_anexo": "false"}) is False
    assert _cfg_incluir_pdf_anexo({"incluir_pdf_anexo": "true"}) is True


@patch("app.api.v1.endpoints.notificaciones_tabs.settings")
@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_envio_cobranza_respeta_incluir_pdf_anexo_false(
    mock_sync,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    mock_settings,
    db: Session,
):
    """Con incluir_pdf_anexo=False no se llama a generar_carta_cobranza_pdf ni se adjunta PDF."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_settings.NOTIFICACIONES_PAQUETE_ESTRICTO = False
    mock_send_email.return_value = (True, None)
    mock_adjunto_fijo.return_value = None

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "prestamo_id": 1,
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
        plantilla.activa = True
        plantilla.asunto = "S"
        plantilla.cuerpo = "C"
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


@patch("app.api.v1.endpoints.notificaciones_tabs.settings")
@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjuntos_fijos_por_caso")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_paquete_estricto_pdf_carta_sin_cabecera_pdf_no_envia_smtp(
    mock_sync,
    mock_adjuntos_caso,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    mock_settings,
    db: Session,
):
    """Con NOTIFICACIONES_PAQUETE_ESTRICTO=True, Carta_Cobranza debe empezar con %PDF o no se envia."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_settings.NOTIFICACIONES_PAQUETE_ESTRICTO = True
    mock_send_email.return_value = (True, None)
    mock_pdf.return_value = b"XXXX"
    mock_adjunto_fijo.return_value = ("Documento.pdf", b"%PDF-1.4 fijo")
    mock_adjuntos_caso.return_value = []

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "prestamo_id": 1,
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
        plantilla.activa = True
        plantilla.asunto = "S"
        plantilla.cuerpo = "C"
        with patch.object(db, "get", return_value=plantilla):
            out = _enviar_correos_items(
                items,
                "Asunto",
                "Cuerpo",
                config_envios,
                get_tipo,
                db,
            )

    assert out["omitidos_paquete_incompleto"] == 1
    assert out["enviados"] == 0
    mock_send_email.assert_not_called()


@patch("app.api.v1.endpoints.notificaciones_tabs.settings")
@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_pago_2_dias_antes_estricto_sin_plantilla_id_envia_correo_sin_pdf_obligatorio(
    mock_sync,
    mock_pdf,
    mock_send_email,
    mock_settings,
    db: Session,
):
    """PAGO_2_DIAS_ANTES_PENDIENTE no exige plantilla en BD ni Carta_Cobranza.pdf bajo paquete estricto."""
    from app.api.v1.endpoints.notificaciones_tabs import (
        _enviar_correos_items,
        _tipo_pago_2_dias_antes_pendiente,
    )

    mock_settings.NOTIFICACIONES_PAQUETE_ESTRICTO = True
    mock_send_email.return_value = (True, None)

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
        }
    ]
    config_envios = {
        "modo_pruebas": False,
        "PAGO_2_DIAS_ANTES_PENDIENTE": {
            "habilitado": True,
            "incluir_pdf_anexo": False,
            "incluir_adjuntos_fijos": False,
        },
    }

    with patch(
        "app.api.v1.endpoints.notificaciones_tabs.get_plantilla_asunto_cuerpo",
        return_value=("Asunto 2d", "Cuerpo 2d"),
    ):
        out = _enviar_correos_items(
            items,
            "Base asunto",
            "Base cuerpo",
            config_envios,
            _tipo_pago_2_dias_antes_pendiente,
            db,
        )

    assert out["enviados"] == 1
    assert out["omitidos_paquete_incompleto"] == 0
    mock_pdf.assert_not_called()
    mock_send_email.assert_called_once()
    assert mock_send_email.call_args[1].get("attachments") is None


@patch("app.api.v1.endpoints.notificaciones_tabs.settings")
@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_envio_cobranza_respeta_incluir_adjuntos_fijos_false(
    mock_sync,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    mock_settings,
    db: Session,
):
    """Con incluir_adjuntos_fijos=False no se llama a get_adjunto_fijo_cobranza_bytes para adjunto fijo."""
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_settings.NOTIFICACIONES_PAQUETE_ESTRICTO = False
    mock_send_email.return_value = (True, None)
    mock_pdf.return_value = b"%PDF-1.4 x"

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "prestamo_id": 1,
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
    mock_pdf.return_value = b"%PDF-1.4 fake-carta"
    mock_adjunto_fijo.return_value = ("Documento.pdf", b"%PDF-1.4 fake-adjunto")

    items = [
        {
            "correo": "cliente@test.com",
            "nombre": "Test",
            "cedula": "V123",
            "prestamo_id": 1,
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
        plantilla.activa = True
        plantilla.asunto = "S"
        plantilla.cuerpo = "C"
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


@patch("app.api.v1.endpoints.notificaciones_tabs.send_email")
@patch("app.api.v1.endpoints.notificaciones_tabs.generar_carta_cobranza_pdf")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjunto_fijo_cobranza_bytes")
@patch("app.api.v1.endpoints.notificaciones_tabs.get_adjuntos_fijos_por_caso")
@patch("app.api.v1.endpoints.notificaciones_tabs.sync_email_config_from_db")
def test_notificacion_llega_a_rapicreditca_con_dos_anexos(
    mock_sync,
    mock_adjuntos_por_caso,
    mock_adjunto_fijo,
    mock_pdf,
    mock_send_email,
    db: Session,
):
    """
    Una notificación en modo pruebas debe llegar a notificaciones@rapicreditca.com
    con exactamente 2 anexos: Carta_Cobranza.pdf y el adjunto fijo (pestaña 3).
    """
    from app.api.v1.endpoints.notificaciones_tabs import _enviar_correos_items

    mock_send_email.return_value = (True, None)
    mock_pdf.return_value = b"%PDF-1.4 fake-carta-cobranza"
    mock_adjunto_fijo.return_value = ("Documento_Anexo.pdf", b"%PDF-1.4 fake-adjunto-fijo")
    mock_adjuntos_por_caso.return_value = []  # sin PDFs por caso extra

    items = [
        {
            "correo": "cliente@ejemplo.com",
            "nombre": "Cliente",
            "cedula": "V12345678",
            "prestamo_id": 1,
            "contexto_cobranza": {"CLIENTES.NOMBRE_COMPLETO": "Cliente", "PRESTAMOS.ID": 1},
        }
    ]
    config_envios = {
        "modo_pruebas": True,
        "email_pruebas": "notificaciones@rapicreditca.com",
        "emails_pruebas": ["notificaciones@rapicreditca.com"],
        "PAGO_1_DIA_ATRASADO": {
            "habilitado": True,
            "plantilla_id": 1,
            "incluir_pdf_anexo": True,
            "incluir_adjuntos_fijos": True,
        },
    }

    def get_tipo(_item):
        return "PAGO_1_DIA_ATRASADO"

    with patch(
        "app.api.v1.endpoints.notificaciones_tabs.get_plantilla_asunto_cuerpo",
        return_value=("Asunto prueba", "<p>Cuerpo</p>"),
    ):
        plantilla = MagicMock()
        plantilla.tipo = "COBRANZA"
        plantilla.activa = True
        plantilla.asunto = "S"
        plantilla.cuerpo = "C"
        with patch.object(db, "get", return_value=plantilla):
            _enviar_correos_items(
                items,
                "Asunto",
                "Cuerpo",
                config_envios,
                get_tipo,
                db,
            )

    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args
    to_email = call_args[0][0] if call_args[0] else call_args[1].get("to_email")
    assert to_email == ["notificaciones@rapicreditca.com"], "El correo debe ir a notificaciones@rapicreditca.com"
    # Confirmar que los adjuntos se pasan SIEMPRE al email cuando están configurados
    attachments = call_args[1].get("attachments")
    assert attachments is not None, "Debe haber adjuntos (se anexan SIEMPRE cuando la config lo pide)"
    assert len(attachments) == 2, "Debe haber exactamente 2 anexos (Carta_Cobranza.pdf + adjunto fijo pestaña 3)"
    names = [a[0] for a in attachments if isinstance(a, tuple)]
    assert "Carta_Cobranza.pdf" in names
    assert "Documento_Anexo.pdf" in names
