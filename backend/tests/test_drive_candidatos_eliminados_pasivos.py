"""Eliminados pasivos Drive: no reaparecen en listados/refresh."""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.services.drive_candidatos_eliminados_pasivos import (
    ORIGEN_PRESTAMO,
    registrar_eliminado_pasivo,
)
from app.services.prestamo_candidatos_drive_guardar import (
    ejecutar_eliminar_candidatos_drive_seleccionados,
)


def test_registrar_pasivo_alta():
    stored: list = []

    class _Sess:
        def execute(self, *_a, **_k):
            m = MagicMock()
            m.scalar_one_or_none.return_value = None
            return m

        def add(self, obj):
            stored.append(obj)

        def flush(self):
            pass

    assert registrar_eliminado_pasivo(
        _Sess(),
        origen=ORIGEN_PRESTAMO,
        cedula_cmp="V20457958",
        sheet_row_number=9699,
    )
    assert stored[0].cedula_cmp == "V20457958"
    assert stored[0].origen == ORIGEN_PRESTAMO
    assert stored[0].sheet_row_number == 9699


def test_eliminar_candidatos_registra_pasivo(monkeypatch):
    cand = PrestamoCandidatoDrive(
        id=7,
        sheet_row_number=100,
        cedula_cmp="V11111111",
        payload={},
    )
    pasivo_calls = []

    def _bulk(db, *, origen, items, usuario_email=None):
        pasivo_calls.append((origen, list(items), usuario_email))
        return len(list(items))

    monkeypatch.setattr(
        "app.services.drive_candidatos_eliminados_pasivos.registrar_eliminados_pasivos_bulk",
        _bulk,
    )

    db = MagicMock()
    select_result = MagicMock()
    select_result.scalars.return_value.all.return_value = [cand]
    delete_result = MagicMock()
    delete_result.rowcount = 1
    db.execute.side_effect = [select_result, delete_result]

    res = ejecutar_eliminar_candidatos_drive_seleccionados(
        db, ids=[7], usuario_email="admin@test.com"
    )
    assert res["eliminados"] == 1
    assert res["pasivos_registrados"] == 1
    assert pasivo_calls[0][0] == ORIGEN_PRESTAMO
    assert pasivo_calls[0][1] == [("V11111111", 100)]
    assert pasivo_calls[0][2] == "admin@test.com"
    db.commit.assert_called_once()
