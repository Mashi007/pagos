from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import deps


class _FakeQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.user


class _FakeSession:
    def __init__(self, user):
        self.user = user

    def query(self, model):
        return _FakeQuery(self)


def _user(email="auditor@example.com", rol="admin", is_active=True):
    now = datetime(2026, 1, 1, 12, 0, 0)
    return SimpleNamespace(
        id=7,
        email=email,
        nombre="Auditor Uno",
        cargo=None,
        rol=rol,
        is_active=is_active,
        created_at=now,
        updated_at=now,
        last_login=None,
    )


def test_staff_user_rechecks_db_after_deactivation(monkeypatch):
    monkeypatch.setattr(deps, "is_configured_env_admin_email", lambda email: False)
    payload = {"sub": "auditor@example.com"}
    db = _FakeSession(_user(is_active=True))

    assert deps.staff_user_from_access_token_payload(db, payload).is_active is True

    db.user = _user(is_active=False)
    with pytest.raises(HTTPException) as exc:
        deps.staff_user_from_access_token_payload(db, payload)

    assert exc.value.status_code == 401


def test_staff_user_rechecks_db_after_role_change(monkeypatch):
    monkeypatch.setattr(deps, "is_configured_env_admin_email", lambda email: False)
    payload = {"sub": "auditor@example.com"}
    db = _FakeSession(_user(rol="admin"))

    assert deps.staff_user_from_access_token_payload(db, payload).rol == "admin"

    db.user = _user(rol="viewer")

    assert deps.staff_user_from_access_token_payload(db, payload).rol == "viewer"
