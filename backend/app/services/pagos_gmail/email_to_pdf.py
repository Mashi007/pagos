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


def _es_parte_eml_anidado(part: Message) -> bool:
    """True si la parte es un .eml / message/rfc822 (reenvio o lote IT Master)."""
    ctype = (part.get_content_type() or "").lower()
    fname = (part.get_filename() or "").strip().lower()
    if ctype == "message/rfc822":
        return True
    if fname.endswith(".eml") or fname.endswith(".msg"):
        return True
    return False


def _parse_nested_eml(part: Message) -> Optional[Message]:
    """Parsea un adjunto .eml / message/rfc822 a Message."""
    ctype = (part.get_content_type() or "").lower()
    try:
        if ctype == "message/rfc822":
            payload = part.get_payload()
            if isinstance(payload, list) and payload:
                first = payload[0]
                if isinstance(first, Message):
                    return first
            if isinstance(payload, Message):
                return payload
        data = _decode_payload(part)
        if not data:
            raw = part.get_payload(decode=False)
            if isinstance(raw, bytes):
                data = raw
            elif isinstance(raw, str):
                data = raw.encode("utf-8", errors="replace")
        if data:
            return BytesParser(policy=policy.default).parsebytes(data)
    except Exception as e:
        logger.warning("[EMAIL_PDF] no se pudo parsear .eml anidado: %s", e)
    return None


def _score_html_aviso(html: str) -> int:
    score = len(html)
    low = html.lower()
    if "rapicredit" in low:
        score += 50000
    if "vencimiento" in low or "cuota" in low:
        score += 20000
    if "<table" in low:
        score += 10000
    if "novedad" in low or "aviso importante" in low:
        score += 15000
    return score


def _score_plain_aviso(text: str) -> int:
    score = len(text)
    low = text.lower()
    if "rapicredit" in low:
        score += 20000
    if "vencimiento" in low or "cuota" in low:
        score += 10000
    if "novedad" in low or "cliente" in low or "total" in low:
        score += 8000
    return score


def _parece_html_aviso(text: str) -> bool:
    low = (text or "").lower()
    return any(
        k in low
        for k in (
            "rapicredit",
            "vencimiento",
            "novedad",
            "aviso importante",
            "<table",
        )
    )


def _get_bodies(msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae (html, plain). Prefiere el HTML mas grande (diseno del aviso),
    no el primer fragmento corto de un reenvio.

    Tambien abre adjuntos .eml / message/rfc822 (lote IT Master / reenvios),
    donde suele estar el HTML real del aviso.
    """
    html_parts: list[str] = []
    plain_parts: list[str] = []
    nested_eml_count = 0

    def collect(m: Message, depth: int = 0) -> None:
        nonlocal nested_eml_count
        if depth > 4:
            return

        if not m.is_multipart():
            ctype = (m.get_content_type() or "").lower()
            body = _decode_text(m)
            if not body.strip():
                return
            if ctype == "text/html":
                html_parts.append(body)
            else:
                plain_parts.append(body)
            return

        for part in m.walk():
            if part is m:
                continue
            ctype = (part.get_content_type() or "").lower()
            if ctype.startswith("multipart/"):
                continue

            if _es_parte_eml_anidado(part):
                nested = _parse_nested_eml(part)
                if nested is not None:
                    nested_eml_count += 1
                    collect(nested, depth + 1)
                continue

            if ctype == "text/html":
                text = _decode_text(part)
                if not text.strip():
                    continue
                # No descartar HTML marcado como attachment si parece el aviso
                if _es_adjunto(part) and not _parece_html_aviso(text):
                    continue
                html_parts.append(text)
            elif ctype == "text/plain":
                if _es_adjunto(part):
                    continue
                text = _decode_text(part)
                if text.strip():
                    plain_parts.append(text)

    collect(msg, 0)

    html: Optional[str] = None
    if html_parts:
        scored = [(_score_html_aviso(h), h) for h in html_parts]
        scored.sort(key=lambda x: x[0], reverse=True)
        html = scored[0][1]

    plain: Optional[str] = None
    if plain_parts:
        scored_p = [(_score_plain_aviso(p), p) for p in plain_parts]
        scored_p.sort(key=lambda x: x[0], reverse=True)
        plain = scored_p[0][1]

    if not html and nested_eml_count:
        logger.info(
            "[EMAIL_PDF] sin HTML util tras abrir %s .eml anidado(s); plain_len=%s",
            nested_eml_count,
            len(plain or ""),
        )
    elif not html:
        logger.info(
            "[EMAIL_PDF] sin parte HTML (nested_eml=%s plain_len=%s)",
            nested_eml_count,
            len(plain or ""),
        )
    return html, plain


def _prefer_headers_from_nested(
    outer: Message,
    html: Optional[str],
) -> Tuple[str, str, str, str]:
    """
    Si el cuerpo util viene de un .eml anidado (aviso recuerda@),
    usar From/To/Date/Subject del anidado cuando el exterior parece reenvio.
    """
    from_h = outer.get("From", "") or ""
    to_h = outer.get("To", "") or ""
    date_h = outer.get("Date", "") or ""
    subj = outer.get("Subject", "") or ""
    if not html:
        return from_h, to_h, date_h, subj

    outer_from = from_h.lower()
    looks_forward = (
        "fwd:" in (subj or "").lower()
        or "rv:" in (subj or "").lower()
        or "itmaster" in outer_from
        or "pagos@" in outer_from
    )
    if not looks_forward:
        return from_h, to_h, date_h, subj

    best: Optional[Message] = None
    best_score = -1

    def scan(m: Message, depth: int = 0) -> None:
        nonlocal best, best_score
        if depth > 4:
            return
        for part in m.walk():
            if part is m:
                continue
            if not _es_parte_eml_anidado(part):
                continue
            nested = _parse_nested_eml(part)
            if nested is None:
                continue
            n_from = (nested.get("From") or "").lower()
            n_subj = (nested.get("Subject") or "").lower()
            score = 0
            if "recuerda@" in n_from or "rapicredit" in n_from:
                score += 100
            if "aviso" in n_subj or "vencimiento" in n_subj:
                score += 50
            if score > best_score:
                best_score = score
                best = nested
            scan(nested, depth + 1)

    scan(outer, 0)
    if best is None or best_score < 50:
        return from_h, to_h, date_h, subj
    return (
        best.get("From", "") or from_h,
        best.get("To", "") or to_h,
        best.get("Date", "") or date_h,
        best.get("Subject", "") or subj,
    )


def _cid_map(msg: EmailMessage) -> dict[str, str]:
    """Content-ID -> data URI (incluye inline, related y .eml anidados)."""
    out: dict[str, str] = {}

    def collect_cids(m: Message, depth: int = 0) -> None:
        if depth > 4:
            return
        for part in m.walk():
            if part is not m and _es_parte_eml_anidado(part):
                nested = _parse_nested_eml(part)
                if nested is not None:
                    collect_cids(nested, depth + 1)
                continue

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
                    if not any(
                        fname.endswith(ext)
                        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
                    ):
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

    collect_cids(msg, 0)
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
    text = re.sub(r"</td>", "\t", text, flags=re.IGNORECASE)
    text = re.sub(r"</th>", "\t", text, flags=re.IGNORECASE)
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


_chromium_ready: Optional[bool] = None


def _ensure_playwright_chromium() -> bool:
    """
    Garantiza el binario de Chromium. En Render el Dashboard a veces omite
    `playwright install` del Build Command; intentamos instalarlo una vez en runtime.
    """
    global _chromium_ready
    if _chromium_ready is True:
        return True

    # Preferir cache persistente del slug de Render
    browsers_path = (
        os.getenv("PLAYWRIGHT_BROWSERS_PATH")
        or "/opt/render/project/.cache/ms-playwright"
    )
    try:
        os.makedirs(browsers_path, exist_ok=True)
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", browsers_path)
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        logger.warning("[EMAIL_PDF] playwright no instalado: %s", e)
        _chromium_ready = False
        return False

    def _executable_ok() -> bool:
        try:
            with sync_playwright() as p:
                exe = p.chromium.executable_path
                return bool(exe and os.path.isfile(exe))
        except Exception:
            return False

    if _executable_ok():
        _chromium_ready = True
        return True

    import subprocess
    import sys

    logger.warning(
        "[EMAIL_PDF] Chromium ausente; ejecutando playwright install chromium "
        "(PLAYWRIGHT_BROWSERS_PATH=%s)",
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
            timeout=600,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        logger.warning("[EMAIL_PDF] playwright install fallo: %s", e)
        _chromium_ready = False
        return False

    ok = _executable_ok()
    _chromium_ready = ok
    if not ok:
        logger.warning("[EMAIL_PDF] Chromium sigue ausente tras playwright install")
    return ok


def _pdf_from_html_chromium(full_doc: str) -> Optional[bytes]:
    """Render HTML -> PDF con Chromium (Playwright)."""
    if not _ensure_playwright_chromium():
        return None
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
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    page.wait_for_timeout(800)
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


def _simplify_html_for_pisa(full_doc: str) -> str:
    """
    xhtml2pdf revienta con tablas de email (padding/width -> availWidth negativo).
    Simplifica estilos y anchos antes de pisa.
    """
    html = full_doc or ""
    # Quitar hojas de estilo externas/complejas del correo (pisa las entiende mal)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.IGNORECASE | re.DOTALL)
    # Atributos width/height en % o px muy grandes
    html = re.sub(r'\swidth\s*=\s*["\'][^"\']*["\']', "", html, flags=re.IGNORECASE)
    html = re.sub(r'\sheight\s*=\s*["\'][^"\']*["\']', "", html, flags=re.IGNORECASE)
    # style= con width/max-width/padding agresivos
    def _clean_style(m: re.Match) -> str:
        style = m.group(1) or ""
        parts = []
        for decl in style.split(";"):
            d = decl.strip().lower()
            if not d:
                continue
            if d.startswith(
                (
                    "width",
                    "max-width",
                    "min-width",
                    "padding",
                    "margin",
                    "position",
                    "float",
                    "display",
                    "left",
                    "right",
                    "top",
                    "bottom",
                )
            ):
                continue
            parts.append(decl.strip())
        if not parts:
            return ""
        return f' style="{"; ".join(parts)}"'

    html = re.sub(
        r'\sstyle\s*=\s*["\']([^"\']*)["\']',
        _clean_style,
        html,
        flags=re.IGNORECASE,
    )
    # cellpadding/cellspacing altos
    html = re.sub(
        r'\scellpadding\s*=\s*["\']?\d+["\']?',
        ' cellpadding="2"',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'\scellspacing\s*=\s*["\']?\d+["\']?',
        ' cellspacing="0"',
        html,
        flags=re.IGNORECASE,
    )
    # Inyectar CSS seguro para pisa
    safe_css = (
        "<style type=\"text/css\">"
        "body{font-family:Helvetica,Arial,sans-serif;font-size:11px;color:#222;}"
        "table{width:100%;border-collapse:collapse;}"
        "td,th{padding:3px;border:0.5px solid #ccc;vertical-align:top;}"
        "img{max-width:280px;}"
        "</style>"
    )
    if re.search(r"<head[^>]*>", html, flags=re.IGNORECASE):
        html = re.sub(
            r"(<head[^>]*>)",
            r"\1" + safe_css,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = safe_css + html
    return html


def _pdf_from_html_xhtml2pdf(full_doc: str) -> Optional[bytes]:
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        logger.warning("[EMAIL_PDF] xhtml2pdf no disponible: %s", e)
        return None
    for label, doc in (
        ("simple", _simplify_html_for_pisa(full_doc)),
        ("raw", full_doc),
    ):
        try:
            buf = BytesIO()
            result = pisa.CreatePDF(doc, dest=buf, encoding="utf-8")
            pdf = buf.getvalue()
            if pdf[:4] == b"%PDF" and len(pdf) > 80:
                if getattr(result, "err", 0):
                    logger.info(
                        "[EMAIL_PDF] pisa PDF (%s) con avisos err=%s",
                        label,
                        result.err,
                    )
                return pdf
            logger.warning(
                "[EMAIL_PDF] pisa no produjo PDF valido (%s) err=%s",
                label,
                getattr(result, "err", None),
            )
        except Exception as e:
            logger.warning("[EMAIL_PDF] xhtml2pdf fallo (%s): %s", label, e)
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
        from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
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
        body_style = ParagraphStyle(
            name="EmailBodyPlain",
            parent=normal,
            fontName="Courier",
            fontSize=8,
            leading=10,
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
        # Preformatted evita que Paragraph recorte/rompa el cuerpo largo del aviso
        story.append(Preformatted(body_clean[:50000], body_style))
        doc.build(story)
        buf.seek(0)
        out = buf.read()
        return out if out[:4] == b"%PDF" else None
    except Exception as e:
        logger.warning("[EMAIL_PDF] reportlab fallo: %s", e)
        return None


def eml_bytes_to_pdf_meta(raw_eml: bytes) -> tuple[Optional[bytes], str]:
    """
    Convierte .eml a PDF. Devuelve (pdf_bytes|None, motor).
    motor: chromium | xhtml2pdf | plain | none
    """
    if not raw_eml:
        return None, "none"
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_eml)
        html, plain = _get_bodies(msg)
        from_h, to_h, date_h, subj = _prefer_headers_from_nested(msg, html)

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
                    return pdf, "chromium"
            if engine in ("xhtml2pdf", "pisa", "auto", "chromium", "playwright", ""):
                pdf = _pdf_from_html_xhtml2pdf(full)
                if pdf:
                    logger.info("[EMAIL_PDF] motor=xhtml2pdf bytes=%s", len(pdf))
                    return pdf, "xhtml2pdf"
            plain = _html_to_plain(html_inlined) or plain

        body_text = plain or ""
        if body_text and ("<" in body_text and ">" in body_text):
            body_text = _html_to_plain(body_text)
        else:
            body_text = unescape(body_text)

        pdf_plain = _pdf_from_plain(
            from_h=from_h,
            to_h=to_h,
            date_h=date_h,
            subj=subj,
            body=body_text,
        )
        if pdf_plain:
            reason = (
                "sin HTML en MIME (stub o .eml no abierto)"
                if not (html and html.strip())
                else "Chromium/xhtml2pdf fallaron; usando texto del HTML"
            )
            logger.warning(
                "[EMAIL_PDF] motor=plain bytes=%s html_len=%s plain_len=%s (%s)",
                len(pdf_plain),
                len(html or ""),
                len(body_text or ""),
                reason,
            )
            return pdf_plain, "plain"
        return None, "none"
    except Exception as e:
        logger.exception("[EMAIL_PDF] eml_bytes_to_pdf: %s", e)
        return None, "none"


def eml_bytes_to_pdf(raw_eml: bytes) -> Optional[bytes]:
    """Convierte .eml a PDF con fidelidad al HTML original (Chromium)."""
    pdf, _motor = eml_bytes_to_pdf_meta(raw_eml)
    return pdf
