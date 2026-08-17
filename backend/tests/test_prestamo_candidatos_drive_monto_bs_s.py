"""Parseo de montos Drive (incl. Bs.S venezolano)."""
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.prestamo_candidatos_drive_normalizacion import parse_decimal_monto_drive
from app.services.prestamo_candidatos_drive_guardar import _motivos_no_100


def test_parse_bs_s_con_miles_y_decimales():
    assert parse_decimal_monto_drive("Bs.S1.575,00") == Decimal("1575.00")
    assert parse_decimal_monto_drive("Bs.S 1.575,00") == Decimal("1575.00")
    assert parse_decimal_monto_drive("BSS1575") == Decimal("1575")


def test_guardar_no_bloquea_por_huella_stale_si_monto_bs_s_parsea(monkeypatch):
    monkeypatch.setattr(
        "app.services.prestamo_candidatos_drive_guardar._cliente_id_por_cedula_normalizada",
        lambda _db, _ced: 22994,
    )
    monkeypatch.setattr(
        "app.services.prestamos.prestamo_reimporte_liquidado.motivo_si_reimporte_liquidado_desde_fechas",
        lambda *a, **k: None,
    )
    payload = {
        "cedula_valida": True,
        "cedula_cmp": "V20457958",
        "col_e_cedula": "V20457958",
        "col_n_total_financiamiento": "Bs.S1.575,00",
        "col_r_numero_cuotas": "15",
        "col_q_fecha": "46246",
        "col_s_modalidad_pago": "Mensual",
        "col_j_analista": "FERNANDA",
        "huella_no_comparable": True,
    }
    ok, motivos, pc = _motivos_no_100(payload, MagicMock(), {"V20457958": 0})
    assert ok is True
    assert motivos == []
    assert pc is not None
    assert pc.total_financiamiento == Decimal("1575.00")
