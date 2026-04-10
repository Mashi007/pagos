# -*- coding: utf-8 -*-
from unittest.mock import patch

from app.core.env_admin_auth import is_configured_env_admin_email


def test_env_admin_match_case_insensitive():
    with patch("app.core.env_admin_auth.settings") as s:
        s.ADMIN_EMAIL = "Admin@Test.com"
        assert is_configured_env_admin_email("admin@test.com") is True


def test_env_admin_mismatch():
    with patch("app.core.env_admin_auth.settings") as s:
        s.ADMIN_EMAIL = "admin@test.com"
        assert is_configured_env_admin_email("other@test.com") is False


def test_env_admin_not_configured():
    with patch("app.core.env_admin_auth.settings") as s:
        s.ADMIN_EMAIL = None
        assert is_configured_env_admin_email("admin@test.com") is False
