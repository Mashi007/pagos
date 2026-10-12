# -*- coding: utf-8 -*-
"""Pagos confirmados manual: solo itmaster@, no cualquier admin."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core import deps
from app.schemas.auth import UserResponse


def _user(email: str, rol: str = "admin") -> UserResponse:
    return UserResponse(
        id=1,
        email=email,
        nombre="T",
        apellido="U",
        cargo="",
        rol=rol,
        is_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        last_login=None,
    )


def test_require_it_master_rechaza_otro_admin():
    other_admin = _user("otro.admin@rapicreditca.com", rol="admin")
    with pytest.raises(HTTPException) as exc:
        deps.require_it_master_admin(current=other_admin)
    assert exc.value.status_code == 403


def test_require_it_master_acepta_itmaster_admin():
    itm = _user("itmaster@rapicreditca.com", rol="admin")
    assert deps.require_it_master_admin(current=itm).email == "itmaster@rapicreditca.com"


def test_require_it_master_rechaza_itmaster_sin_rol_admin():
    itm_viewer = _user("itmaster@rapicreditca.com", rol="viewer")
    with pytest.raises(HTTPException) as exc:
        deps.require_it_master_admin(current=itm_viewer)
    assert exc.value.status_code == 403
