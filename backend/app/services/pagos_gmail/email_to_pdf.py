"""
Convierte el correo raw (.eml) a PDF con aspecto cercano al original de Gmail.

Prioridad:
1) Cuerpo text/html renderizado con xhtml2pdf (maquetacion del aviso).
2) Fallback texto plano con entidades HTML decodificadas (reportlab).
"""
from __future__ import annotations

import logging
import re
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from html import unescape
from io import BytesIO
from typing import Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

logger = logging.getLogger(__name__)

# Emojis / simbolos fuera del BMP suelen romper fuentes de xhtml2pdf/reportlab
_RE_NON_BMP = re.compile(r"[\U00010000-\U0010FFFF]")
_RE_SCRIPT_STYLE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not payload:
        raw = part.get_payload(decode=False)
        if isinstance(raw, str):
            return raw
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _es_adjunto(part: Message) -> bool:
    disp = str(part.get("Content-Disposition") or "").lower()
    return "attachment" in disp


def _get_bodies(msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae (html, plain) del mensaje, prefiriendo partes inline (no adjuntos).
    Recorre todo el arbol (reenvios multipart/related inclusive).
    """
    html: Optional[str] = None
    plain: Optional[str] = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype.startswith("multipart/"):
                continue
            if _es_adjunto(part):
                continue
            if ctype == "text/html" and html is None:
                html = _decode_payload(part)
            elif ctype == "text/plain" and plain is None:
                plain = _decode_payload(part)
    else:
        ctype = (msg.get_content_type() or "").lower()
        body = _decode_payload(msg)
        if ctype == "text/html":
            html = body
        else:
            plain = body

    return html, plain


def _html_to_plain(html: str) -> str:
    if not html:
        return ""
    text = _RE_SCRIPT_STYLE.sub(" ", html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize_visual_text(s: str) -> str:
    if not s:
        return ""
    s = unescape(s)
    s = _RE_NON_BMP.sub(" ", s)
    return s


def _wrap_email_html(
    *,
    from_h: str,
    to_h: str,
    date_h: str,
    subj: str,
    body_html: str,
) -> str:
    """Documento XHTML para xhtml2pdf con cabecera tipo correo + cuerpo HTML."""
    inner = body_html or ""
    m_body = re.search(r"<body[^>]*>(.*)</body>", inner, re.IGNORECASE | re.DOTALL)
    if m_body:
        inner = m_body.group(1)
    else:
        inner = _RE_SCRIPT_STYLE.sub("", inner)

    fh = xml_escape(_sanitize_visual_text(from_h))
    th = xml_escape(_sanitize_visual_text(to_h))
    dh = xml_escape(_sanitize_visual_text(date_h))
    sh = xml_escape(_sanitize_visual_text(subj))

    inner = unescape(inner)
    inner = _RE_NON_BMP.sub(" ", inner)

    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml'><head>"
        "<meta http-equiv='Content-Type' content='text/html; charset=utf-8'/>"
        "<style type='text/css'>"
        "body{font-family:Helvetica,Arial,sans-serif;font-size:11pt;color:#222;"
        "margin:18px;line-height:1.35;}"
        ".email-meta{border-bottom:1px solid #ccc;padding-bottom:10px;margin-bottom:14px;}"
        ".email-meta .row{margin:2px 0;}"
        ".email-meta .lbl{font-weight:bold;color:#444;display:inline-block;min-width:58px;}"
        ".email-body img{max-width:100%;}"
        "table{border-collapse:collapse;max-width:100%;}"
        "td,th{padding:4px;}"
        "a{color:#0b57d0;}"
        "</style></head><body>"
        "<div class='email-meta'>"
        f"<div class='row'><span class='lbl'>De:</span> {fh}</div>"
        f"<div class='row'><span class='lbl'>Para:</span> {th}</div>"
        f"<div class='row'><span class='lbl'>Fecha:</span> {dh}</div>"
        f"<div class='row'><span class='lbl'>Asunto:</span> {sh}</div>"
        "</div>"
        f"<div class='email-body'>{inner}</div>"
        "</body></html>"
    )


def _pdf_from_html(full_doc: str) -> Optional[bytes]:
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        logger.warning("[EMAIL_PDF] xhtml2pdf no disponible: %s", e)
        return None
    try:
        buf = BytesIO()
        result = pisa.CreatePDF(full_doc, dest=buf, encoding="utf-8")
        pdf = buf.getvalue()
        if pdf[:4] == b"%PDF" and len(pdf) > 80:
            if getattr(result, "err", 0):
                logger.info("[EMAIL_PDF] pisa PDF con avisos err=%s", result.err)
            return pdf
        logger.warning(
            "[EMAIL_PDF] pisa no produjo PDF valido err=%s",
            getattr(result, "err", None),
        )
    except Exception as e:
        logger.warning("[EMAIL_PDF] xhtml2pdf fallo: %s", e)
    return None


def _pdf_from_plain(
    *,
    from_h: str,
    to_h: str,
    date_h: str,
    subj: str,
    body: str,
) -> Optional[bytes]:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as e:
        logger.warning("[EMAIL_PDF] reportlab no disponible: %s", e)
        return None

    def _esc(s: str) -> str:
        s = _sanitize_visual_text(s or "")
        return xml_escape(s)[:20000]

    try:
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
        story = [
            Paragraph("De:", title_style),
            Paragraph(_esc(from_h), normal),
            Spacer(1, 0.3 * cm),
            Paragraph("Para:", title_style),
            Paragraph(_esc(to_h), normal),
            Spacer(1, 0.3 * cm),
            Paragraph("Fecha:", title_style),
            Paragraph(_esc(date_h), normal),
            Spacer(1, 0.3 * cm),
            Paragraph("Asunto:", title_style),
            Paragraph(_esc(subj), normal),
            Spacer(1, 0.5 * cm),
            Paragraph("Cuerpo:", title_style),
        ]
        body_clean = _sanitize_visual_text(body) if body else "(sin cuerpo)"
        body_para = xml_escape(body_clean).replace("\n", "<br/>")
        story.append(Paragraph(body_para[:50000], normal))
        doc.build(story)
        buf.seek(0)
        out = buf.read()
        return out if out[:4] == b"%PDF" else None
    except Exception as e:
        logger.warning("[EMAIL_PDF] reportlab fallo: %s", e)
        return None


def eml_bytes_to_pdf(raw_eml: bytes) -> Optional[bytes]:
    """
    Convierte el contenido raw de un correo (.eml) a PDF.

    Usa el HTML del mensaje cuando existe (aspecto del aviso original);
    si no, texto plano con entidades decodificadas.
    """
    if not raw_eml:
        return None
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_eml)
        from_h = msg.get("From", "") or ""
        to_h = msg.get("To", "") or ""
        date_h = msg.get("Date", "") or ""
        subj = msg.get("Subject", "") or ""
        html, plain = _get_bodies(msg)

        if html and html.strip():
            full = _wrap_email_html(
                from_h=from_h,
                to_h=to_h,
                date_h=date_h,
                subj=subj,
                body_html=html,
            )
            pdf = _pdf_from_html(full)
            if pdf:
                return pdf
            plain = _html_to_plain(html) or plain

        body_text = plain or ""
        if body_text and ("<" in body_text and ">" in body_text):
            body_text = _html_to_plain(body_text)
        else:
            body_text = unescape(body_text)

        return _pdf_from_plain(
            from_h=from_h,
            to_h=to_h,
            date_h=date_h,
            subj=subj,
            body=body_text,
        )
    except Exception as e:
        logger.exception("[EMAIL_PDF] eml_bytes_to_pdf: %s", e)
        return None
