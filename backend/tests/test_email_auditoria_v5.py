# -*- coding: utf-8 -*-
from app.core.email import (
    EMAIL_AUDIT_BUILD,
    EMAIL_AUDIT_COBRANZA,
    EMAIL_AUDIT_NOTIFICACIONES,
    EMAIL_ITMASTER,
    resolver_destinos_auditoria,
)


def test_notificaciones_bcc_solo_itmaster():
    r = resolver_destinos_auditoria(
        to_emails=["cliente@gmail.com", "itmaster@rapicreditca.com"],
        cc_emails=["itmaster@rapicreditca.com"],
        bcc_emails=["cobranza@rapicreditca.com", "notificaciones@rapicreditca.com", "otro@x.com"],
        servicio="notificaciones",
    )
    assert r["build"] == EMAIL_AUDIT_BUILD
    assert r["to"] == ["cliente@gmail.com"]
    assert r["cc"] == []
    assert r["bcc"] == [EMAIL_ITMASTER]
    assert r["itmaster_presente"] is True
    assert r["bloqueados_encontrados"] == []
    assert EMAIL_AUDIT_NOTIFICACIONES not in r["bcc"]
    assert EMAIL_AUDIT_COBRANZA not in r["bcc"]


def test_recibos_sigue_auditoria_sin_itmaster_bcc():
    r = resolver_destinos_auditoria(
        to_emails=["cliente@gmail.com"],
        bcc_emails=["itmaster@rapicreditca.com"],
        servicio="recibos",
    )
    assert r["to"] == ["cliente@gmail.com"]
    assert EMAIL_ITMASTER not in r["bcc"]
    assert EMAIL_AUDIT_NOTIFICACIONES in r["bcc"]
    assert EMAIL_AUDIT_COBRANZA in r["bcc"]


def test_to_solo_itmaster_fallback_notificaciones():
    r = resolver_destinos_auditoria(
        to_emails=["itmaster@rapicreditca.com"], servicio="notificaciones"
    )
    assert r["to"] == [EMAIL_AUDIT_NOTIFICACIONES]
    assert r["bcc"] == [EMAIL_ITMASTER]
