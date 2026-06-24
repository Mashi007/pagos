"""Reglas V/E (max 1 APROBADO) vs J (varios) en candidatos Drive."""
import os
import sys
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
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678"),
        db,
        {"V12345678": 0},
    )
    assert ok is True
    assert motivos == []


def test_ve_con_varios_liquidados_y_cero_aprobado_permite(monkeypatch):
    """V con solo LIQUIDADO (0 APROBADO) puede guardar desde Drive."""
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 99,
    )
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678"),
        db,
        {"V12345678": 0},
    )
    assert ok is True
    assert motivos == []


def test_ve_con_un_aprobado_bloquea(monkeypatch):
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678"),
        db,
        {"V12345678": 1},
    )
    assert ok is False
    assert any("APROBADO" in m for m in motivos)


def test_duplicada_en_hoja_no_bloquea_guardado(monkeypatch):
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 99,
    )
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("V12345678", duplicada_en_hoja=True),
        db,
        {"V12345678": 0},
    )
    assert ok is True
    assert not any("duplicada" in m.lower() for m in motivos)


def test_j_con_varios_aprobados_no_bloquea_por_cupo_ve(monkeypatch):
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 50,
    )
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    db = MagicMock()
    ok, motivos, _pc = _motivos_no_100(
        _payload_base("J123456789", cedula_es_tipo_j=True),
        db,
        {"J123456789": 4},
    )
    assert ok is True
    assert not any("tipo V o E" in m for m in motivos)
