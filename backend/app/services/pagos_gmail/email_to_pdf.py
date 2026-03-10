"""
Convierte el correo raw (.eml) a PDF para visualización directa (corregir columnas sin abrir cliente de correo).
"""
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from io import BytesIO
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _get_body_text(msg: EmailMessage) -> str:
    """Extrae el cuerpo en texto plano (decodificado)."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = payload.decode(charset, errors="replace")
                    except Exception:
                        body = payload.decode("utf-8", errors="replace")
                break
            if ctype == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html = payload.decode(charset, errors="replace")
                    except Exception:
                        html = payload.decode("utf-8", errors="replace")
                    body = _html_to_plain(html)
                break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace")
            except Exception:
                body = payload.decode("utf-8", errors="replace")
        if (msg.get_content_type() or "").lower() == "text/html":
            body = _html_to_plain(body)
    return (body or "").strip()


def _html_to_plain(html: str) -> str:
    """Quita etiquetas HTML y normaliza espacios."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub(r"&lt;", "<", text, flags=re.IGNORECASE)
    text = re.sub(r"&gt;", ">", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def eml_bytes_to_pdf(raw_eml: bytes) -> Optional[bytes]:
    """
    Convierte el contenido raw de un correo (.eml) a PDF legible.
    Incluye: De, Para, Fecha, Asunto y cuerpo en texto plano.
    Returns PDF bytes o None si falla.
    """
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_eml)
        from_h = msg.get("From", "") or ""
        to_h = msg.get("To", "") or ""
        date_h = msg.get("Date", "") or ""
        subj = msg.get("Subject", "") or ""
        body = _get_body_text(msg)

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        title_style = ParagraphStyle(
            name="EmailHeader",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=10,
            spaceAfter=4,
        )

        story = []
        story.append(Paragraph("De:", title_style))
        story.append(Paragraph(_escape(from_h), normal))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Para:", title_style))
        story.append(Paragraph(_escape(to_h), normal))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Fecha:", title_style))
        story.append(Paragraph(_escape(date_h), normal))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Asunto:", title_style))
        story.append(Paragraph(_escape(subj), normal))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Cuerpo:", title_style))
        body_para = _escape(body) if body else "(sin cuerpo)"
        body_para = body_para.replace("\n", "<br/>")
        story.append(Paragraph(body_para, normal))

        doc.build(story)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def _escape(s: str) -> str:
    """Escapa para ReportLab (evitar XML inválido)."""
    if not s:
        return ""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s[:10000]
