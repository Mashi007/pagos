# -*- coding: utf-8 -*-
"""URL pública del API para PDF/Excel cuando no hay Request."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_effective_api_public_base_url, settings
from app.services.estado_cuenta_pdf import base_url_y_token_recibo_para_pdf_estado_cuenta


def test_get_effective_api_public_base_url_prefers_backend():
    with patch.object(settings, "BACKEND_PUBLIC_URL", "https://api.example.com/"), patch.object(
        settings, "FRONTEND_PUBLIC_URL", "https://wrong.example/pagos"
    ), patch.object(settings, "GOOGLE_REDIRECT_URI", ""):
        assert get_effective_api_public_base_url() == "https://api.example.com"


def test_get_effective_api_public_base_url_from_frontend_origin():
    with patch.object(settings, "BACKEND_PUBLIC_URL", None), patch.object(
        settings, "FRONTEND_PUBLIC_URL", "https://myapp.onrender.com/pagos"
    ), patch.object(settings, "GOOGLE_REDIRECT_URI", ""):
        assert get_effective_api_public_base_url() == "https://myapp.onrender.com"


def test_get_effective_api_public_base_url_from_google_redirect():
    with patch.object(settings, "BACKEND_PUBLIC_URL", ""), patch.object(
        settings, "FRONTEND_PUBLIC_URL", ""
    ), patch.object(
        settings,
        "GOOGLE_REDIRECT_URI",
        "https://oauth-host.onrender.com/api/v1/pagos/gmail/callback",
    ):
        assert get_effective_api_public_base_url() == "https://oauth-host.onrender.com"


def test_get_effective_api_public_base_url_empty_when_nothing():
    with patch.object(settings, "BACKEND_PUBLIC_URL", None), patch.object(
        settings, "FRONTEND_PUBLIC_URL", None
    ), patch.object(settings, "GOOGLE_REDIRECT_URI", None):
        assert get_effective_api_public_base_url() == ""


def test_base_url_y_token_usa_request_cuando_hay_request():
    req = MagicMock()
    req.base_url = "https://from-request.example/api/v1/"
    base, tok = base_url_y_token_recibo_para_pdf_estado_cuenta(
        "V12345678", request=req, token_expire_hours=2
    )
    assert base == "https://from-request.example/api/v1"
    assert isinstance(tok, str) and len(tok) > 10


def test_base_url_y_token_sin_request_usa_settings():
    with patch.object(settings, "BACKEND_PUBLIC_URL", "https://api.example.com/"), patch.object(
        settings, "FRONTEND_PUBLIC_URL", ""
    ), patch.object(settings, "GOOGLE_REDIRECT_URI", ""):
        base, tok = base_url_y_token_recibo_para_pdf_estado_cuenta("V12345678", request=None)
    assert base == "https://api.example.com"
    assert isinstance(tok, str) and len(tok) > 10
