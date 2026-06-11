"""Tests para actualización de fecha Q en candidatos Drive."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from app.models.drive import DriveRow
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.prestamo_candidatos_drive_actualizar import (
    actualizar_fecha_q_candidato_drive,
)


def test_actualizar_fecha_q_actualiza_snapshot_y_drive():
    drive = DriveRow(sheet_row_number=42, col_q="04/07/2026")
    cand = PrestamoCandidatoDrive(
        id=7,
        sheet_row_number=42,
        cedula_cmp="V12345678",
        payload={
            "col_q_fecha": "04/07/2026",
            "col_q_fecha_iso": None,
            "col_q_fecha_ambigua": True,
            "col_n_total_financiamiento": "1000",
            "col_r_numero_cuotas": "12",
            "col_s_modalidad_pago": "MENSUAL",
            "huella_no_comparable": True,
        },
    )
    db = MagicMock()
    db.get.side_effect = lambda model, key: {
        (PrestamoCandidatoDrive, 7): cand,
        (DriveRow, 42): drive,
    }.get((model, key))

    res = actualizar_fecha_q_candidato_drive(db, fila_id=7, fecha_q="2026-07-04")

    assert res["ok"] is True
    assert res["col_q_fecha_iso"] == "2026-07-04"
    assert cand.payload["col_q_fecha"] == "2026-07-04"
    assert cand.payload["col_q_fecha_iso"] == "2026-07-04"
    assert cand.payload["col_q_fecha_ambigua"] is False
    assert cand.payload["huella_no_comparable"] is False
    assert drive.col_q == "2026-07-04"
    db.commit.assert_called_once()


def test_actualizar_fecha_q_rechaza_formato_no_iso():
    cand = PrestamoCandidatoDrive(
        id=1,
        sheet_row_number=1,
        cedula_cmp="V11111111",
        payload={"col_q_fecha": "x"},
    )
    db = MagicMock()
    db.get.return_value = cand

    with pytest.raises(HTTPException) as exc:
        actualizar_fecha_q_candidato_drive(db, fila_id=1, fecha_q="04/07/2026")
    assert exc.value.status_code == 400
