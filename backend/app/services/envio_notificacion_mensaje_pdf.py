"""Genera PDF del cuerpo del correo (snapshot HTML o texto plano) para constancia descargable."""

from __future__ import annotations

import io
import logging
import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Optional
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from app.models.envio_notificacion import EnvioNotificacion

logger = logging.getLogger(__name__)


class _TextFromHTML(HTMLParser):
    """Extrae texto legible; ignora script/style."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        if t in ("script", "style"):
            self._skip = True
        elif t in ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4"):
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style"):
            self._skip = False
        elif t in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "table"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t\f\v]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _html_to_plain(html: str) -> str:
    p = _TextFromHTML()
    try:
        p.feed(html)
        p.close()
        return p.text() or html
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)


def _reportlab_pdf_from_plain(text: str) -> Optional[bytes]:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as e:
        logger.warning("[MENSAJE_PDF] reportlab no disponible: %s", e)
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    story = []
    safe = escape(text).replace("\n", "<br/>")
    story.append(Paragraph(safe, styles["Normal"]))
    story.append(Spacer(1, 12))
    doc.build(story)
    out = buf.getvalue()
    return out if out[:4] == b"%PDF" else None


def generar_mensaje_envio_pdf_bytes(envio: "EnvioNotificacion") -> Optional[bytes]:
    """
    PDF del cuerpo del mensaje. Prefiere HTML guardado (maquetación); si no hay, usa texto plano.
    """
    html_snippet = (getattr(envio, "mensaje_html", None) or "").strip()
    texto = (getattr(envio, "mensaje_texto", None) or "").strip()
    if not html_snippet and not texto:
        return None

    if not html_snippet:
        inner = (
            "<pre style='white-space:pre-wrap;font-family:Helvetica,Arial,sans-serif;font-size:11pt;'>"
            f"{escape(texto)}</pre>"
        )
    else:
        inner = html_snippet

    full_doc = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml'><head>"
        "<meta http-equiv='Content-Type' content='text/html; charset=utf-8'/>"
        "<style type='text/css'>"
        "body{font-family:Helvetica,Arial,sans-serif;font-size:11pt;margin:24px;}"
        "table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #444;padding:6px;}"
        "</style></head><body>"
        f"{inner}</body></html>"
    )

    try:
        from xhtml2pdf import pisa

        buf = io.BytesIO()
        result = pisa.CreatePDF(full_doc, dest=buf, encoding="utf-8")
        pdf = buf.getvalue()
        if pdf[:4] == b"%PDF" and len(pdf) > 80:
            if getattr(result, "err", 0):
                logger.info("[MENSAJE_PDF] pisa genero PDF con avisos err=%s", result.err)
            return pdf
        logger.warning("[MENSAJE_PDF] pisa no produjo PDF valido err=%s", getattr(result, "err", None))
    except Exception as e:
        logger.warning("[MENSAJE_PDF] xhtml2pdf fallo: %s", e)

    plain = texto if texto else _html_to_plain(html_snippet)
    if not plain:
        return None
    return _reportlab_pdf_from_plain(plain)
