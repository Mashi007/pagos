# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware.audit_helpers import (
    audit_entity_from_path,
    format_http_error_message,
    is_auth_credential_path,
    redact_body_for_audit,
    skip_failed_audit_persist,
)


def test_is_auth_credential_path():
    assert is_auth_credential_path("/api/v1/auth/login")
    assert is_auth_credential_path("/API/V1/auth/refresh")
    assert is_auth_credential_path("/api/v1/auth/forgot-password")
    assert not is_auth_credential_path("/api/v1/pagos")


def test_redact_body_auth_path_never_leaks_password():
    body = {"email": "a@b.com", "password": "secret123"}
    out = redact_body_for_audit("/api/v1/auth/login", body)
    assert out == {"_redacted": "credentials"}


def test_redact_body_strips_sensitive_keys():
    body = {"foo": 1, "access_token": "x", "nested": {"password": "p"}}
    out = redact_body_for_audit("/api/v1/usuarios", body)
    assert out["foo"] == 1
    assert out["access_token"] == "[REDACTED]"
    assert out["nested"]["password"] == "[REDACTED]"


def test_skip_failed_audit_persist_pagos_409_post():
    assert skip_failed_audit_persist("/api/v1/pagos", "POST", 409)
    assert skip_failed_audit_persist("/api/v1/pagos/batch", "post", 409)
    assert skip_failed_audit_persist("/api/v1/pagos/upload", "POST", 409)
    assert not skip_failed_audit_persist("/api/v1/pagos", "POST", 400)
    assert not skip_failed_audit_persist("/api/v1/pagos", "GET", 409)
    assert not skip_failed_audit_persist("/api/v1/clientes", "POST", 409)


def test_audit_entity_from_path():
    ent, eid = audit_entity_from_path("/api/v1/prestamos/42/cuotas")
    assert eid == 42
    assert isinstance(ent, str) and len(ent) > 0


def test_format_http_error_message():
    class H(dict):
        pass

    h = H({"X-Request-ID": "abc-123"})
    assert "409" in format_http_error_message(409, h)
    assert "abc-123" in format_http_error_message(409, h)
