"""Sesión SMTP reutilizada en lotes de notificaciones."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.email import SmtpLoteSession, _smtp_cfg_session_key


def test_smtp_lote_reutiliza_misma_sesion():
    cfg = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "notificaciones@rapicreditca.com",
        "smtp_password": "secret",
        "smtp_use_tls": "true",
    }
    server = MagicMock()
    server.sendmail.return_value = {}

    with patch("app.core.email._smtp_connect_and_login", return_value=server) as connect:
        sess = SmtpLoteSession()
        sess.deliver(
            cfg=cfg,
            port=587,
            use_tls=True,
            from_addr="notificaciones@rapicreditca.com",
            all_recipients=["a@b.com"],
            msg_bytes=b"raw",
            smtp_session_metadata={},
            t0_smtp=0.0,
        )
        sess.deliver(
            cfg=cfg,
            port=587,
            use_tls=True,
            from_addr="notificaciones@rapicreditca.com",
            all_recipients=["c@d.com"],
            msg_bytes=b"raw2",
            smtp_session_metadata={},
            t0_smtp=0.0,
        )
        sess.close()

    assert connect.call_count == 1
    assert server.sendmail.call_count == 2


def test_smtp_lote_reconecta_si_cambia_cuenta():
    cfg_a = {
        "smtp_host": "smtp.gmail.com",
        "smtp_user": "a@test.com",
        "smtp_password": "x",
    }
    cfg_b = {
        "smtp_host": "smtp.gmail.com",
        "smtp_user": "b@test.com",
        "smtp_password": "y",
    }
    servers = [MagicMock(), MagicMock()]
    for s in servers:
        s.sendmail.return_value = {}

    with patch(
        "app.core.email._smtp_connect_and_login",
        side_effect=servers,
    ) as connect:
        sess = SmtpLoteSession()
        sess.deliver(
            cfg=cfg_a,
            port=587,
            use_tls=True,
            from_addr="a@test.com",
            all_recipients=["x@y.com"],
            msg_bytes=b"1",
            smtp_session_metadata=None,
            t0_smtp=0.0,
        )
        sess.deliver(
            cfg=cfg_b,
            port=587,
            use_tls=True,
            from_addr="b@test.com",
            all_recipients=["x@y.com"],
            msg_bytes=b"2",
            smtp_session_metadata=None,
            t0_smtp=0.0,
        )
        sess.close()

    assert connect.call_count == 2
    assert _smtp_cfg_session_key(cfg_a, 587, True) != _smtp_cfg_session_key(cfg_b, 587, True)
