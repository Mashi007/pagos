# -*- coding: utf-8 -*-
"""Simulacion politica email audit v5.3: CCO unico sin solapes."""
from app.core.email import (
    EMAIL_AUDIT_BUILD,
    EMAIL_AUDIT_COBRANZA,
    EMAIL_AUDIT_NOTIFICACIONES,
    resolver_destinos_auditoria,
)


def test_recibos_cco_sin_to_auditoria_ni_pagos():
    r = resolver_destinos_auditoria(
        to_emails=["cliente@gmail.com", "itmaster@rapicreditca.com"],
        cc_emails=["itmaster@rapicreditca.com"],
        bcc_emails=["itmaster@rapicreditca.com", "otro@x.com", "notificaciones@rapicreditca.com"],
        servicio="recibos",
    )
    assert r["build"] == EMAIL_AUDIT_BUILD
    assert r["itmaster_presente"] is False
    assert r["to"] == ["cliente@gmail.com"]
    assert r["notificaciones_en_to"] is False
    assert r["cobranza_en_to"] is False
    assert r["notificaciones_en_bcc"] is True
    assert r["cobranza_en_bcc"] is True
    assert "otro@x.com" in r["bcc"]
    assert r["bcc"].count(EMAIL_AUDIT_NOTIFICACIONES) == 1
    assert r["force_to_copia"] == []


def test_notificaciones_tambien_cco_sin_copia_pagos():
    r = resolver_destinos_auditoria(to_emails=["a@b.com"], servicio="notificaciones")
    assert r["to"] == ["a@b.com"]
    assert r["notificaciones_en_bcc"] is True
    assert r["cobranza_en_bcc"] is True
    assert r["force_to_copia"] == []


def test_sin_cliente_to_respaldo_notif():
    r = resolver_destinos_auditoria(to_emails=["itmaster@rapicreditca.com"], servicio="recibos")
    assert r["to"] == [EMAIL_AUDIT_NOTIFICACIONES]
    assert EMAIL_AUDIT_NOTIFICACIONES not in r["bcc"]
    assert EMAIL_AUDIT_COBRANZA in r["bcc"]
