# -*- coding: utf-8 -*-
"""Tests conversion .eml -> PDF con HTML (evidencias / Gmail)."""
from email.message import EmailMessage

from app.services.pagos_gmail.email_to_pdf import (
    eml_bytes_to_pdf,
    _html_to_plain,
    _inline_cids,
    _wrap_email_html_print,
)


def _eml_html() -> bytes:
    msg = EmailMessage()
    msg["From"] = "recuerda@rapicreditca.com"
    msg["To"] = "PABLOUSVE@GMAIL.COM"
    msg["Subject"] = "AVISO IMPORTANTE"
    msg["Date"] = "Sat, 08 Aug 2026 14:51:32 +0000"
    html = (
        "<html><head><style>.titulo{color:#0b1f4d;font-weight:bold}</style></head>"
        "<body>"
        "<div class=\"titulo\">Aviso Importante</div>"
        "<p>Notificaci&#243;n de Vencimiento de Cuotas</p>"
        "<p>Cliente: Pablo Enrique Peraza Guerra</p>"
        "<table><tr><td>TOTAL</td><td>$640.00</td></tr></table>"
        "</body></html>"
    )
    msg.set_content("plain fallback Notificaci&#243;n")
    msg.add_alternative(html, subtype="html")
    return msg.as_bytes()


def test_html_to_plain_decodes_entities():
    assert "ó" in _html_to_plain("Notificaci&#243;n")
    assert "&#243;" not in _html_to_plain("Notificaci&#243;n")


def test_inline_cids_replaces_src():
    html = '<img src="cid:logo123@rapicredit">'
    out = _inline_cids(html, {"logo123@rapicredit": "data:image/png;base64,AAA"})
    assert "cid:" not in out
    assert "data:image/png;base64,AAA" in out


def test_wrap_preserves_styles():
    raw = (
        "<html><head><style>.x{color:orange}</style></head>"
        "<body><h1 class=\"x\">Hola</h1></body></html>"
    )
    doc = _wrap_email_html_print(
        from_h="a@b.com",
        to_h="c@d.com",
        date_h="Sat, 08 Aug 2026",
        subj="AVISO",
        body_html=raw,
    )
    assert ".x{color:orange}" in doc
    assert "AVISO" in doc
    assert "gmail-print-chrome" in doc


def test_eml_bytes_to_pdf_renders_html_without_raw_entities():
    pdf = eml_bytes_to_pdf(_eml_html())
    assert pdf is not None
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 200
    assert b"&#243;" not in pdf
