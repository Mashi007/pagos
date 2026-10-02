# -*- coding: utf-8 -*-
"""OTP publico: SMTP remitente tucuenta@."""
from app.core.email_cuentas import (
    BUZON_SMTP_COBRANZA,
    BUZON_SMTP_TUCUENTA,
    contenido_es_otp_estado_cuenta_publico,
    smtp_config_codigo_otp_cobranza,
    smtp_config_codigo_otp_tucuenta,
    smtp_config_recibos_tucuenta,
    TIPO_TAB_CODIGO_OTP,
)
from app.core.email_config_holder import get_smtp_config


def test_contenido_es_otp_estado_cuenta_por_asunto_y_cuerpo():
    assert contenido_es_otp_estado_cuenta_publico(
        "Codigo para estado de cuenta - RapiCredit",
        "Estimado(a) X,\n\nTu codigo de verificacion es: 123456\n\nValido por 2 horas.",
    )
    assert not contenido_es_otp_estado_cuenta_publico(
        "Recibo de pago",
        "Adjunto su recibo.",
    )


def test_smtp_config_codigo_otp_usa_cuenta_tucuenta_en_bd():
    cuentas = [
        {"smtp_user": "pagos@rapicreditca.com", "smtp_password": "x", "from_email": "pagos@rapicreditca.com"},
        {
            "smtp_user": BUZON_SMTP_TUCUENTA,
            "smtp_password": "secret",
            "from_email": BUZON_SMTP_TUCUENTA,
            "smtp_host": "smtp.gmail.com",
        },
    ]
    cfg = smtp_config_codigo_otp_tucuenta(cuentas)
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA
    assert cfg["from_email"] == BUZON_SMTP_TUCUENTA
    assert cfg["smtp_password"] == "secret"


def test_otp_usa_tucuenta_aunque_cuenta2_tenga_from_cobranza():
    cuentas = [
        {
            "smtp_user": BUZON_SMTP_TUCUENTA,
            "from_email": BUZON_SMTP_COBRANZA,
            "smtp_password": "pw-ok",
        }
    ]
    cfg = smtp_config_codigo_otp_tucuenta(cuentas)
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA
    assert cfg["smtp_password"] == "pw-ok"


def test_smtp_config_codigo_otp_sin_cuenta_canonical_tucuenta():
    cfg = smtp_config_codigo_otp_tucuenta([{"smtp_user": "pagos@rapicreditca.com"}])
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA
    assert cfg["from_email"] == BUZON_SMTP_TUCUENTA


def test_compat_alias_cobranza_apunta_a_tucuenta():
    cuentas = [
        {
            "smtp_user": BUZON_SMTP_TUCUENTA,
            "smtp_password": "pw",
            "from_email": BUZON_SMTP_TUCUENTA,
        }
    ]
    assert smtp_config_codigo_otp_cobranza(cuentas)["smtp_user"] == BUZON_SMTP_TUCUENTA


def test_recibos_usa_tucuenta_aunque_cuenta2_sea_cobranza():
    cuentas = [
        {"smtp_user": "pagos@rapicreditca.com"},
        {
            "smtp_user": BUZON_SMTP_COBRANZA,
            "smtp_password": "pw-cobranza",
            "from_email": BUZON_SMTP_COBRANZA,
        },
        {
            "smtp_user": BUZON_SMTP_TUCUENTA,
            "smtp_password": "pw-tucuenta",
            "from_email": BUZON_SMTP_TUCUENTA,
        },
    ]
    cfg = smtp_config_recibos_tucuenta(cuentas)
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA
    assert cfg["smtp_password"] == "pw-tucuenta"


def test_get_smtp_config_estado_cuenta_codigo_otp(monkeypatch):
    import app.core.email_config_holder as holder

    monkeypatch.setattr(
        holder,
        "_cuentas_data",
        {
            "cuentas": [
                {
                    "smtp_user": BUZON_SMTP_TUCUENTA,
                    "from_email": BUZON_SMTP_TUCUENTA,
                    "smtp_password": "pw",
                }
            ]
        },
    )
    monkeypatch.setattr(holder, "sync_from_db", lambda: None)
    cfg = get_smtp_config(servicio="estado_cuenta_otp")
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA


def test_get_smtp_config_estado_cuenta_cuenta2_por_asignacion(monkeypatch):
    import app.core.email_config_holder as holder

    monkeypatch.setattr(
        holder,
        "_cuentas_data",
        {
            "cuentas": [
                {},
                {
                    "smtp_user": BUZON_SMTP_TUCUENTA,
                    "from_email": BUZON_SMTP_TUCUENTA,
                    "smtp_password": "pw",
                },
            ],
            "asignacion": {"estado_cuenta": 2},
        },
    )
    monkeypatch.setattr(holder, "sync_from_db", lambda: None)
    cfg = get_smtp_config(servicio="estado_cuenta")
    assert cfg["smtp_user"] == BUZON_SMTP_TUCUENTA
