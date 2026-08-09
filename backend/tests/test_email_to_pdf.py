# -*- coding: utf-8 -*-
"""Tests conversion .eml -> PDF con HTML (evidencias / Gmail)."""
from email.message import EmailMessage

from app.services.pagos_gmail.email_to_pdf import eml_bytes_to_pdf, _html_to_plain


def _eml_html() -> bytes:
    msg = EmailMessage()
    msg["From"] = "recuerda@rapicreditca.com"
    msg["To"] = "PABLOUSVE@GMAIL.COM"
    msg["Subject"] = "AVISO IMPORTANTE"
    msg["Date"] = "Sat, 08 Aug 2026 14:51:32 +0000"
    html = (
        "<html><body><h1>Aviso Importante</h1>"
        "<p>Notificaci&#243;n de Vencimiento de Cuotas</p>"
        "<p>Cliente: Pablo Enrique Peraza Guerra</p>"
        "<p>Total: $640.00</p>"
        "</body></html>"
    )
    msg.set_content("plain fallback Notificaci&#243;n")
    msg.add_alternative(html, subtype="html")
    return msg.as_bytes()


def test_html_to_plain_decodes_entities():
    assert "ó" in _html_to_plain("Notificaci&#243;n")
    assert "&#243;" not in _html_to_plain("Notificaci&#243;n")


def test_eml_bytes_to_pdf_renders_html_without_raw_entities():
    pdf = eml_bytes_to_pdf(_eml_html())
    assert pdf is not None
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 200
    # El PDF no debe arrastrar entidades literales tipicas del bug
    assert b"&#243;" not in pdf
