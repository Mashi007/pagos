# -*- coding: utf-8 -*-
"""Persistencia tokens cobranza@ — BD primaria, archivo espejo opcional."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.pagos_gmail import credentials as creds_mod
from app.services.pagos_gmail.credentials import CLAVE_COBRANZA_GMAIL_TOKENS


@pytest.fixture
def mock_db():
    store: dict = {}

    db = MagicMock()

    def _get(_model, clave):
        if clave not in store:
            return None
        row = MagicMock()
        row.valor = store[clave]
        return row

    def _add(row):
        store[row.clave] = row.valor

    db.get.side_effect = _get
    db.add.side_effect = _add
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db, store


def test_save_tokens_bd_when_file_fails(mock_db):
    db, store = mock_db
    with patch.object(creds_mod, "_cobranza_tokens_path_resolved", return_value="/var/data/nope.json"):
        with patch.object(creds_mod.os, "makedirs", side_effect=PermissionError("denied")):
            path = creds_mod.save_cobranza_gmail_tokens(
                refresh_token="rt-test",
                access_token="at-test",
                db=db,
            )
    assert path.startswith("postgresql:")
    assert CLAVE_COBRANZA_GMAIL_TOKENS in store
    data = json.loads(store[CLAVE_COBRANZA_GMAIL_TOKENS])
    assert data["refresh_token"] == "rt-test"
    assert data["token"] == "at-test"


def test_load_tokens_from_bd_when_no_file():
    with patch.object(creds_mod, "_cobranza_tokens_path_resolved", return_value="/var/data/missing.json"):
        with patch.object(creds_mod.os.path, "isfile", return_value=False):
            with patch.object(
                creds_mod,
                "_load_cobranza_tokens_from_db",
                return_value={"refresh_token": "rt-bd"},
            ):
                payload, source = creds_mod.load_cobranza_gmail_token_payload()
    assert source == "bd"
    assert payload["refresh_token"] == "rt-bd"


def test_save_raises_if_both_fail(mock_db):
    db, store = mock_db
    db.commit.side_effect = RuntimeError("db down")
    with patch.object(creds_mod, "_cobranza_tokens_path_resolved", return_value="/var/data/nope.json"):
        with patch.object(creds_mod.os, "makedirs", side_effect=PermissionError("denied")):
            with pytest.raises(OSError):
                creds_mod.save_cobranza_gmail_tokens(refresh_token="rt", db=db)
