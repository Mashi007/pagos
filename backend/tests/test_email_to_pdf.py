# -*- coding: utf-8 -*-
"""Tests conversion .eml -> PDF con HTML (evidencias / Gmail)."""
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.pagos_gmail.email_to_pdf import (
    eml_bytes_to_pdf,
    eml_bytes_to_pdf_meta,
    _get_bodies,
    _html_to_plain,
    _inline_cids,
    _wrap_email_html_print,
)
from email import policy
from email.parser import BytesParser


def _aviso_html() -> str:
    return (
        "<html><head><style>.titulo{color:#0b1f4d;font-weight:bold}</style></head>"
        "<body>"
        "<div class=\"titulo\">Aviso Importante</div>"
        "<p>Notificaci&#243;n de Vencimiento de Cuotas</p>"
        "<p>Caracas, 09/08/2026</p>"
        "<h2>Novedad</h2>"
        "<p>Cliente: Pablo Enrique Peraza Guerra</p>"
        "<table><tr><td>TOTAL</td><td>$640.00</td></tr></table>"
        "</body></html>"
    )


def _eml_html() -> bytes:
    msg = EmailMessage()
    msg["From"] = "recuerda@rapicreditca.com"
    msg["To"] = "PABLOUSVE@GMAIL.COM"
    msg["Subject"] = "AVISO IMPORTANTE"
    msg["Date"] = "Sat, 08 Aug 2026 14:51:32 +0000"
    msg.set_content("plain fallback Notificaci&#243;n")
    msg.add_alternative(_aviso_html(), subtype="html")
    return msg.as_bytes()


def _eml_forward_with_nested_octet_stream() -> bytes:
    """Stub externo + aviso real en adjunto .eml (application/octet-stream)."""
    inner = EmailMessage()
    inner["From"] = "recuerda@rapicreditca.com"
    inner["To"] = "oseluismatheus17@gmail.com"
    inner["Subject"] = "AVISO IMPORTANTE"
    inner["Date"] = "Sun, 09 Aug 2026 23:00:48 +0000"
    inner.set_content(
        "Aviso Importante\nNotificacion de Vencimiento de Cuotas\nCaracas, 09/08/2026\n"
    )
    inner.add_alternative(_aviso_html(), subtype="html")
    inner_bytes = inner.as_bytes()

    outer = MIMEMultipart()
    outer["From"] = "itmaster@rapicreditca.com"
    outer["To"] = "pagos@rapicreditca.com"
    outer["Subject"] = "Fwd: lote evidencias"
    outer["Date"] = "Sun, 09 Aug 2026 23:05:00 +0000"
    outer.attach(
        MIMEText(
            "Aviso Importante\nNotificacion de Vencimiento de Cuotas\nCaracas, 09/08/2026\n",
            "plain",
            "utf-8",
        )
    )
    att = MIMEApplication(inner_bytes, Name="aviso.eml")
    att.add_header("Content-Disposition", "attachment", filename="aviso.eml")
    outer.attach(att)
    return outer.as_bytes()


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


def test_get_bodies_unwraps_nested_eml_octet_stream():
    raw = _eml_forward_with_nested_octet_stream()
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    html, plain = _get_bodies(msg)
    assert html is not None
    assert "Novedad" in html
    assert "TOTAL" in html
    assert plain is not None


def test_nested_eml_pdf_includes_novedad_text():
    raw = _eml_forward_with_nested_octet_stream()
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    html, _plain = _get_bodies(msg)
    assert html is not None
    plain_from_html = _html_to_plain(html)
    assert "Novedad" in plain_from_html
    assert "640" in plain_from_html

    pdf, motor = eml_bytes_to_pdf_meta(raw)
    assert pdf is not None
    assert pdf[:4] == b"%PDF"
    assert motor in ("chromium", "xhtml2pdf", "plain")
    assert len(pdf) > 800
