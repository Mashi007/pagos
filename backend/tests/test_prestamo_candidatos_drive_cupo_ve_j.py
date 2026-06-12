"""Reglas V/E (max 1 APROBADO) vs J (varios) en candidatos Drive."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.prestamo_candidatos_drive_guardar import _motivos_no_100


def _payload_base(cedula_cmp: str, **extra):
    p = {
        "cedula_valida": True,
        "duplicada_en_hoja": False,
        "cedula_cmp": cedula_cmp,
        "col_e_cedula": cedula_cmp,
        "col_n_total_financiamiento": "1000",
        "col_r_numero_cuotas": "12",
        "col_q_fecha": "2026-01-15",
        "col_s_modalidad_pago": "MENSUAL",
        "col_j_analista": "Ana",
        "huella_no_comparable": False,
    }
    p.update(extra)
    return p


def test_ve_con_prestamo_liquidado_no_bloquea_por_conteo_aprobado(monkeypatch):
    """V con 0 APROBADO debe poder guardar aunque haya préstamos en otros estados."""
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 99,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678"),
        db,
        {"V12345678": 0},
    )
    assert ok is True
    assert motivos == []


def test_ve_con_un_aprobado_bloquea():
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678"),
        db,
        {"V12345678": 1},
    )
    assert ok is False
    assert any("APROBADO" in m for m in motivos)


def test_j_con_varios_aprobados_no_bloquea_por_cupo_ve(monkeypatch):
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 50,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("J123456789", cedula_es_tipo_j=True),
        db,
        {"J123456789": 4},
    )
    assert ok is True
    assert not any("tipo V o E" in m for m in motivos)


def test_guardar_una_fila_exitosa_no_falla_por_actualizar_conteo(monkeypatch):
    from app.api.v1.endpoints import prestamos as prestamos_routes
    from app.services import prestamo_candidatos_drive_guardar as svc

    candidato = SimpleNamespace(
        payload=_payload_base("V12345678"),
        cedula_cmp="V12345678",
    )
    db = MagicMock()
    db.scalar.return_value = candidato

    monkeypatch.setattr(
        svc,
        "conteo_prestamos_aprobados_por_cedula_norm",
        lambda _db: {"V12345678": 0},
    )
    monkeypatch.setattr(
        svc,
        "_motivos_no_100",
        lambda _payload, _db, _counts: (True, [], SimpleNamespace()),
    )
    monkeypatch.setattr(
        prestamos_routes,
        "crear_prestamo_servicio_interno",
        lambda _db, _pc, _current_user: SimpleNamespace(id=123),
    )

    out = svc.ejecutar_guardar_candidatos_drive_una_fila(
        db,
        current_user=SimpleNamespace(rol="admin"),
        sheet_row_number=25,
    )

    assert out["ok"] is True
    assert out["insertados_ok"] == 1
    db.delete.assert_called_once_with(candidato)
    db.commit.assert_called_once()
