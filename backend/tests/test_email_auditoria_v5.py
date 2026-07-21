# -*- coding: utf-8 -*-
"""Simulacion politica email audit v5 (sin SMTP)."""
from app.core.email import (
    EMAIL_AUDIT_BUILD,
    EMAIL_AUDIT_COBRANZA,
    EMAIL_AUDIT_NOTIFICACIONES,
    resolver_destinos_auditoria,
)


def test_itmaster_eliminado_y_notif_en_to():
    r = resolver_destinos_auditoria(
        to_emails=["cliente@gmail.com", "itmaster@rapicreditca.com"],
        cc_emails=["itmaster@rapicreditca.com"],
        bcc_emails=["itmaster@rapicreditca.com", "otro@x.com"],
    )
    assert r["build"] == EMAIL_AUDIT_BUILD
    assert r["itmaster_presente"] is False
    assert "itmaster@rapicreditca.com" not in r["envelope_rcpt"]
    assert "itmaster@rapicreditca.com" not in r["to"]
    assert EMAIL_AUDIT_NOTIFICACIONES in r["to"]
    assert EMAIL_AUDIT_COBRANZA in r["to"]
    assert r["notificaciones_en_to"] is True
    assert r["cobranza_en_to"] is True
    assert r["force_to_copia"] == [EMAIL_AUDIT_NOTIFICACIONES]
    # bcc no debe conservar auditoria ni itmaster
    assert EMAIL_AUDIT_NOTIFICACIONES not in r["bcc"]
    assert EMAIL_AUDIT_COBRANZA not in r["bcc"]


def test_cliente_solo_sigue_y_auditoria_en_to():
    r = resolver_destinos_auditoria(to_emails=["a@b.com"])
    assert r["to"][0] == "a@b.com"
    assert EMAIL_AUDIT_NOTIFICACIONES in r["to"]
    assert EMAIL_AUDIT_COBRANZA in r["to"]
