# -*- coding: utf-8 -*-
"""OTP publico: SMTP remitente cobranza@."""
from app.core.email_cuentas import (
    BUZON_SMTP_COBRANZA,
    smtp_config_codigo_otp_cobranza,
    TIPO_TAB_CODIGO_OTP,
)
from app.core.email_config_holder import get_smtp_config


def test_smtp_config_codigo_otp_usa_cuenta_cobranza_en_bd():
    cuentas = [
        {"smtp_user": "pagos@rapicreditca.com", "smtp_password": "x", "from_email": "pagos@rapicreditca.com"},
        {
            "smtp_user": BUZON_SMTP_COBRANZA,
            "smtp_password": "secret",
            "from_email": BUZON_SMTP_COBRANZA,
            "smtp_host": "smtp.gmail.com",
        },
    ]
    cfg = smtp_config_codigo_otp_cobranza(cuentas)
    assert cfg["smtp_user"] == BUZON_SMTP_COBRANZA
    assert cfg["from_email"] == BUZON_SMTP_COBRANZA
    assert cfg["smtp_password"] == "secret"


def test_smtp_config_codigo_otp_sin_cuenta_canonica_cobranza():
    cfg = smtp_config_codigo_otp_cobranza([{"smtp_user": "pagos@rapicreditca.com"}])
    assert cfg["smtp_user"] == BUZON_SMTP_COBRANZA
    assert cfg["from_email"] == BUZON_SMTP_COBRANZA


def test_get_smtp_config_estado_cuenta_codigo_otp(monkeypatch):
    import app.core.email_config_holder as holder

    monkeypatch.setattr(
        holder,
        "_cuentas_data",
        {
            "cuentas": [
                {
                    "smtp_user": BUZON_SMTP_COBRANZA,
                    "from_email": BUZON_SMTP_COBRANZA,
                    "smtp_password": "pw",
                }
            ]
        },
    )
    monkeypatch.setattr(holder, "sync_from_db", lambda: None)
    cfg = get_smtp_config(servicio="estado_cuenta", tipo_tab=TIPO_TAB_CODIGO_OTP)
    assert cfg["smtp_user"] == BUZON_SMTP_COBRANZA
