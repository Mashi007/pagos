"""Regresiones de atomicidad para guardado desde candidatos Drive."""

from types import SimpleNamespace
import sys

from app.services import prestamo_candidatos_drive_guardar as guardar


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows
        self.commits = 0
        self.rollbacks = 0
        self.deleted = []

    def execute(self, _stmt):
        return _FakeExecuteResult(self._rows)

    def scalar(self, _stmt):
        return self._rows[0] if self._rows else None

    def delete(self, row):
        self.deleted.append(row)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _patch_valid_candidate(monkeypatch):
    pc = object()
    monkeypatch.setattr(guardar, "conteo_prestamos_por_cedula_norm", lambda _db: {})
    monkeypatch.setattr(guardar, "_motivos_no_100", lambda *_args: (True, [], pc))
    return pc


def test_guardar_candidatos_drive_masivo_usa_transaccion_externa(monkeypatch):
    row = SimpleNamespace(payload={"cedula_cmp": "J123"}, sheet_row_number=7, cedula_cmp="J123")
    db = _FakeDb([row])
    pc = _patch_valid_candidate(monkeypatch)
    calls = []

    def fake_crear(db_arg, pc_arg, current_user_arg, *, commit_transaction=True):
        calls.append((db_arg, pc_arg, current_user_arg, commit_transaction))

    monkeypatch.setitem(
        sys.modules,
        "app.api.v1.endpoints.prestamos",
        SimpleNamespace(crear_prestamo_servicio_interno=fake_crear),
    )

    result = guardar.ejecutar_guardar_candidatos_drive_validados_100(
        db, current_user=SimpleNamespace(email="admin@example.com")
    )

    assert result["insertados_ok"] == 1
    assert calls == [(db, pc, SimpleNamespace(email="admin@example.com"), False)]
    assert db.deleted == [row]
    assert db.commits == 1
    assert db.rollbacks == 0


def test_guardar_candidatos_drive_una_fila_usa_transaccion_externa(monkeypatch):
    row = SimpleNamespace(payload={"cedula_cmp": "J123"}, sheet_row_number=7, cedula_cmp="J123")
    db = _FakeDb([row])
    pc = _patch_valid_candidate(monkeypatch)
    calls = []
    current_user = SimpleNamespace(email="admin@example.com")

    def fake_crear(db_arg, pc_arg, current_user_arg, *, commit_transaction=True):
        calls.append((db_arg, pc_arg, current_user_arg, commit_transaction))

    monkeypatch.setitem(
        sys.modules,
        "app.api.v1.endpoints.prestamos",
        SimpleNamespace(crear_prestamo_servicio_interno=fake_crear),
    )

    result = guardar.ejecutar_guardar_candidatos_drive_una_fila(
        db, current_user=current_user, sheet_row_number=7
    )

    assert result["ok"] is True
    assert calls == [(db, pc, current_user, False)]
    assert db.deleted == [row]
    assert db.commits == 1
    assert db.rollbacks == 0
