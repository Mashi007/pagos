"""
Convierte el correo raw (.eml) a PDF fidelidad alta (evidencia legal).

Prioridad:
1) HTML del mensaje + imagenes CID, renderizado con Chromium (Playwright)
   -> aspecto cercano a "Imprimir" de Gmail.
2) Fallback xhtml2pdf.
3) Fallback texto plano (reportlab).
"""
from __future__ import annotations

import base64
import logging
import os
import re
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from html import unescape
from io import BytesIO
from typing import Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

logger = logging.getLogger(__name__)

_RE_NON_BMP = re.compile(r"[\U00010000-\U0010FFFF]")
_RE_SCRIPT = re.compile(
    r"<script[^>]*>.*?</script>",
    re.IGNORECASE | re.DOTALL,
)
def _decode_payload(part: Message) -> bytes:
    payload = part.get_payload(decode=True)
    if payload:
        return payload
    raw = part.get_payload(decode=False)
    if isinstance(raw, str):
        return raw.encode("utf-8", errors="replace")
    if isinstance(raw, bytes):
        return raw
    return b""


def _decode_text(part: Message) -> str:
    data = _decode_payload(part)
    if not data:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _es_adjunto(part: Message) -> bool:
    disp = str(part.get("Content-Disposition") or "").lower()
    return "attachment" in disp and "inline" not in disp


def _get_bodies(msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae (html, plain). Prefiere el HTML mas grande (diseno del aviso),
    no el primer fragmento corto de un reenvio.
    """
    html_parts: list[str] = []
    plain: Optional[str] = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype.startswith("multipart/"):
                continue
            if ctype == "text/html":
                if _es_adjunto(part):
                    continue
                text = _decode_text(part)
                if text.strip():
                    html_parts.append(text)
            elif ctype == "text/plain" and plain is None and not _es_adjunto(part):
                plain = _decode_text(part)
    else:
        ctype = (msg.get_content_type() or "").lower()
        body = _decode_text(msg)
        if ctype == "text/html":
            html_parts.append(body)
        else:
            plain = body

    html: Optional[str] = None
    if html_parts:
        # Preferir el que parece el aviso (logo / cuotas) o el mas largo
        scored = []
        for h in html_parts:
            score = len(h)
            low = h.lower()
            if "rapicredit" in low:
                score += 50000
            if "vencimiento" in low or "cuota" in low:
                score += 20000
            if "<table" in low:
                score += 10000
            scored.append((score, h))
        scored.sort(key=lambda x: x[0], reverse=True)
        html = scored[0][1]
    return html, plain


def _cid_map(msg: EmailMessage) -> dict[str, str]:
    """Content-ID -> data URI (incluye inline y related)."""
    out: dict[str, str] = {}
    for part in msg.walk():
        cid_raw = part.get("Content-ID") or part.get("Content-Id") or ""
        if not cid_raw:
            continue
        cid = cid_raw.strip().strip("<>").strip()
        if not cid:
            continue
        data = _decode_payload(part)
        if not data:
            continue
        ctype = (part.get_content_type() or "application/octet-stream").split(";")[0].strip()
        if not ctype.startswith("image/") and ctype not in (
            "application/octet-stream",
            "application/pdf",
        ):
            # Solo embeber imagenes tipicas de logo/firma
            if not ctype.startswith("image/"):
                fname = (part.get_filename() or "").lower()
                if not any(fname.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
                    continue
                if ctype == "application/octet-stream":
                    if fname.endswith(".png"):
                        ctype = "image/png"
                    elif fname.endswith((".jpg", ".jpeg")):
                        ctype = "image/jpeg"
                    elif fname.endswith(".gif"):
                        ctype = "image/gif"
                    else:
                        ctype = "image/png"
        b64 = base64.b64encode(data).decode("ascii")
        data_uri = f"data:{ctype};base64,{b64}"
        out[cid] = data_uri
        out[cid.lower()] = data_uri
        # Gmail a veces usa solo la parte local del CID
        if "@" in cid:
            local = cid.split("@", 1)[0]
            out[local] = data_uri
            out[local.lower()] = data_uri
    return out


def _inline_cids(html: str, cid_map: dict[str, str]) -> str:
    if not html or not cid_map:
        return html or ""

    def _lookup(cid: str) -> Optional[str]:
        c = unescape(cid).strip().strip("<>")
        return cid_map.get(c) or cid_map.get(c.lower())

    def repl_src(m: re.Match) -> str:
        uri = _lookup(m.group(1))
        return f'src="{uri}"' if uri else m.group(0)

    def repl_href(m: re.Match) -> str:
        uri = _lookup(m.group(1))
        return f'href="{uri}"' if uri else m.group(0)

    def repl_css(m: re.Match) -> str:
        uri = _lookup(m.group(1))
        return f'url("{uri}")' if uri else m.group(0)

    html = re.sub(
        r'src\s*=\s*["\']cid:([^"\']+)["\']',
        repl_src,
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'href\s*=\s*["\']cid:([^"\']+)["\']',
        repl_href,
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'url\(\s*[\'"]?cid:([^\'")\s]+)[\'"]?\s*\)',
        repl_css,
        html,
        flags=re.IGNORECASE,
    )
    return html


def _html_to_plain(html: str) -> str:
    if not html:
        return ""
    text = _RE_SCRIPT.sub(" ", html)
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


def _extract_head_body(html: str) -> Tuple[str, str]:
    """Devuelve (head_inner, body_inner) preservando styles del correo."""
    html = html or ""
    html = _RE_SCRIPT.sub("", html)
    m_head = re.search(r"<head[^>]*>(.*?)</head>", html, re.IGNORECASE | re.DOTALL)
    m_body = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
    head = m_head.group(1) if m_head else ""
    if m_body:
        body = m_body.group(1)
    else:
        body = html
    return head, body


def _wrap_email_html_print(
    *,
    from_h: str,
    to_h: str,
    date_h: str,
    subj: str,
    body_html: str,
) -> str:
    """
    Documento HTML listo para Chromium (estilo Imprimir de Gmail).
    Conserva CSS/HTML del aviso original.
    """
    head_inner, body_inner = _extract_head_body(body_html)
    fh = xml_escape(_sanitize_visual_text(from_h))
    th = xml_escape(_sanitize_visual_text(to_h))
    dh = xml_escape(_sanitize_visual_text(date_h))
    sh = xml_escape(_sanitize_visual_text(subj))

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
{head_inner}
<style type="text/css">
  @page {{ size: A4; margin: 12mm; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    color: #202124;
    margin: 0;
    padding: 0;
    background: #fff;
  }}
  .gmail-print-chrome {{
    border-bottom: 1px solid #dadce0;
    padding: 0 0 14px 0;
    margin: 0 0 18px 0;
  }}
  .gmail-print-chrome h1 {{
    font-size: 18px;
    font-weight: 700;
    margin: 0 0 10px 0;
    color: #202124;
  }}
  .gmail-print-meta {{
    font-size: 12.5px;
    line-height: 1.45;
    color: #3c4043;
  }}
  .gmail-print-meta .from {{ font-weight: 600; color: #202124; }}
  .gmail-print-body {{
    max-width: 100%;
  }}
  .gmail-print-body img {{
    max-width: 100% !important;
    height: auto !important;
  }}
  .gmail-print-body table {{
    max-width: 100% !important;
  }}
</style>
</head>
<body>
  <div class="gmail-print-chrome">
    <h1>{sh or "(sin asunto)"}</h1>
    <div class="gmail-print-meta">
      <div class="from">{fh or "(sin remitente)"}</div>
      <div>Para: {th or "(sin destinatario)"}</div>
      <div>{dh}</div>
    </div>
  </div>
  <div class="gmail-print-body">
    {body_inner}
  </div>
</body>
</html>
"""


def _pdf_from_html_chromium(full_doc: str) -> Optional[bytes]:
    """Render HTML -> PDF con Chromium (Playwright)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        logger.warning("[EMAIL_PDF] playwright no instalado: %s", e)
        return None

    # En algunos hosts (Render) hace falta no-sandbox
    launch_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--font-render-hinting=none",
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=launch_args)
            try:
                page = browser.new_page()
                page.set_content(full_doc, wait_until="load", timeout=60000)
                page.wait_for_timeout(300)
                pdf = page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=False,
                    margin={
                        "top": "10mm",
                        "right": "10mm",
                        "bottom": "12mm",
                        "left": "10mm",
                    },
                )
            finally:
                browser.close()
        if pdf and pdf[:4] == b"%PDF" and len(pdf) > 80:
            return pdf
        logger.warning("[EMAIL_PDF] chromium no produjo PDF valido")
    except Exception as e:
        logger.warning("[EMAIL_PDF] chromium fallo: %s", e)
    return None


def _pdf_from_html_xhtml2pdf(full_doc: str) -> Optional[bytes]:
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
    Convierte .eml a PDF con fidelidad al HTML original (Chromium).
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

        engine = (os.getenv("EMAIL_PDF_ENGINE") or "chromium").strip().lower()

        if html and html.strip():
            html_inlined = _inline_cids(html, _cid_map(msg))
            full = _wrap_email_html_print(
                from_h=from_h,
                to_h=to_h,
                date_h=date_h,
                subj=subj,
                body_html=html_inlined,
            )
            pdf: Optional[bytes] = None
            if engine in ("chromium", "playwright", "auto", ""):
                pdf = _pdf_from_html_chromium(full)
                if pdf:
                    logger.info("[EMAIL_PDF] motor=chromium bytes=%s", len(pdf))
                    return pdf
            if engine in ("xhtml2pdf", "pisa", "auto", "chromium", "playwright", ""):
                pdf = _pdf_from_html_xhtml2pdf(full)
                if pdf:
                    logger.info("[EMAIL_PDF] motor=xhtml2pdf bytes=%s", len(pdf))
                    return pdf
            plain = _html_to_plain(html_inlined) or plain

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
