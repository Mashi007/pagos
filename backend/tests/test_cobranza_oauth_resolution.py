# -*- coding: utf-8 -*-
"""OAuth cobranza@ — resolución Opción A (cliente compartido con Informe de pagos)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.pagos_gmail import credentials as creds_mod


BITT_ID = (
    "336520671892-bitt72qkft83fnogumcmjfn4v8o0bn8e.apps.googleusercontent.com"
)
SECRET_BD = "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12"
SECRET_ENV = "GOCSPX-stale-render-env3456"


@pytest.fixture
def mock_settings():
    with patch.object(creds_mod, "settings") as st:
        st.AUDITORIA_EMAIL_GOOGLE_CLIENT_ID = None
        st.AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET = None
        yield st


def test_shared_client_prefers_informe_pagos_secret(mock_settings):
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_ID = BITT_ID
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET = SECRET_ENV
    with patch.object(
        creds_mod, "_informe_pagos_oauth_pair", return_value=(BITT_ID, SECRET_BD)
    ):
        cid, csec, meta = creds_mod.resolve_cobranza_oauth_client_pair()
    assert cid == BITT_ID
    assert csec == SECRET_BD
    assert meta["client_secret_source"] == "informe_pagos_bd"


def test_env_secret_when_no_informe_pagos(mock_settings):
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_ID = BITT_ID
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET = SECRET_ENV
    with patch.object(creds_mod, "_informe_pagos_oauth_pair", return_value=(None, None)):
        cid, csec, meta = creds_mod.resolve_cobranza_oauth_client_pair()
    assert cid == BITT_ID
    assert csec == SECRET_ENV
    assert meta["client_secret_source"] == "auditoria_email_env"


def test_client_id_from_informe_when_render_id_missing(mock_settings):
    with patch.object(
        creds_mod, "_informe_pagos_oauth_pair", return_value=(BITT_ID, SECRET_BD)
    ):
        cid, csec, meta = creds_mod.resolve_cobranza_oauth_client_pair()
    assert cid == BITT_ID
    assert csec == SECRET_BD
    assert meta["client_id_source"] == "informe_pagos_bd"


def test_mismatch_client_id_uses_env_secret_only(mock_settings):
    other_id = "336520671892-other.apps.googleusercontent.com"
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_ID = other_id
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET = SECRET_ENV
    with patch.object(
        creds_mod, "_informe_pagos_oauth_pair", return_value=(BITT_ID, SECRET_BD)
    ):
        cid, csec, meta = creds_mod.resolve_cobranza_oauth_client_pair()
    assert cid == other_id
    assert csec == SECRET_ENV
    assert meta["client_secret_source"] == "auditoria_email_env"


def test_config_status_shared_source(mock_settings):
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_ID = BITT_ID
    mock_settings.AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET = SECRET_ENV
    mock_settings.GOOGLE_CLIENT_ID = None
    mock_settings.GOOGLE_CLIENT_SECRET = None
    with patch.object(
        creds_mod, "_informe_pagos_oauth_pair", return_value=(BITT_ID, SECRET_BD)
    ):
        st = creds_mod.cobranza_oauth_config_status()
    assert st["oauth_client_source"] == "shared_client_informe_pagos_bd"
    assert st["oauth_client_secret_source"] == "informe_pagos_bd"
    assert st["oauth_client_secret_suffix"] == SECRET_BD[-4:]
    assert st["oauth_env_secret_suffix"] == SECRET_ENV[-4:]
