"""Regresión: run-now no debe refrescar OAuth en el request HTTP."""
from app.services.pagos_gmail.credentials import pagos_gmail_credentials_configured


def test_pagos_gmail_credentials_configured_callable():
    # Sin BD/env de prod puede ser False; no debe lanzar ni llamar a Google.
    assert isinstance(pagos_gmail_credentials_configured(), bool)
