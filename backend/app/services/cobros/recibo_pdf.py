"""
Generacion del recibo PDF para reportes de pago (modulo Cobros).
Diseno profesional con encabezado, resumen estructurado y bloque narrativo.
"""
import html
import io
import logging
from datetime import date
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

from app.services.tasa_cambio_service import fecha_hoy_caracas

WHATSAPP_LINK = "https://wa.me/584244579934"
WHATSAPP_DISPLAY = "424-4579934"
CONTACTO_COBRANZA = "cobranza@rapicreditca.com"

# Texto para cliente cuando aun no hay cuota(s) aplicada(s) al abono (PDF y API publica)
RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE = "Revisando Pago"

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"


def _referencia_display(referencia_interna: str) -> str:
    ref = (referencia_interna or "").strip()
    if not ref:
        return "-"
    return ref if ref.startswith("#") else f"#{ref}"


def _is_placeholder_text(value: str) -> bool:
    txt = (value or "").strip().upper()
    return txt in {"", "-", "N/A", "NA", "NONE", "NULL", "NULO"}


def _normalize_monto_display(monto: str) -> str:
    txt = (monto or "").strip()
    up = txt.upper()
    if "USDT" in up:
        txt = txt.replace("USDT", "USD")
    return txt


def _formato_monto_venezolano(n: float) -> str:
    """Miles con punto, decimales con coma (ej. 2.000.000,00)."""
    neg = n < 0
    n = abs(n)
    ip, dec = f"{n:.2f}".split(".")
    rev = ip[::-1]
    chunks = [rev[i : i + 3][::-1] for i in range(0, len(rev), 3)]
    int_fmt = ".".join(reversed(chunks))
    if neg:
        int_fmt = "-" + int_fmt
    return f"{int_fmt},{dec}"


def _formato_decimal_ve(n: float) -> str:
    """Numero con coma decimal (ej. tasa 527,79)."""
    ip, dec = f"{n:.2f}".split(".")
    return f"{ip},{dec}"


def _parse_numero_desde_texto_monto(txt: str) -> Optional[float]:
    """Extrae el monto numerico de cadenas como '2000000.00 BS' o '1.234,56'."""
    import re

    t = (txt or "").strip()
    if not t:
        return None
    t = _normalize_monto_display(t)
    while True:
        t2 = re.sub(r"\s+(BS\.?|USD|USDT|VES|VEF)\s*$", "", t, flags=re.IGNORECASE).strip()
        if t2 == t:
            break
        t = t2
    if not t:
        return None
    # Formato VE: 2.000.000,50
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t_norm = t.replace(".", "").replace(",", ".")
        else:
            t_norm = t.replace(",", "")
    elif t.count(",") == 1 and t.count(".") == 0:
        parts = t.split(",")
        if len(parts[-1]) <= 2 and parts[-1].isdigit():
            t_norm = parts[0].replace(".", "") + "." + parts[-1]
        else:
            t_norm = t.replace(",", ".")
    else:
        t_norm = t.replace(",", "")
    try:
        return float(t_norm)
    except ValueError:
        m = re.search(r"[-]?\d+(?:\.\d+)?", t.replace(",", "."))
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
        return None


def _etiqueta_moneda(moneda_codigo: Optional[str], monto_upper: str) -> str:
    c = (moneda_codigo or "").strip().upper()
    if c == "USD" or "USD" in monto_upper:
        return "USD"
    return "Bs."


def _celda_monto_con_simbolo(raw: str, sym: str) -> str:
    """Formatea un monto numerico (saldos) en estilo VE con una sola moneda."""
    if not raw or (raw or "").strip() == "-":
        return "-"
    n = _parse_numero_desde_texto_monto(raw)
    if n is None:
        try:
            n = float(str(raw).replace(",", "").strip())
        except ValueError:
            t = (raw or "").strip()
            return f"{t} {sym}".strip()
    return f"{_formato_monto_venezolano(n)} {sym}"


def _monto_tabla_y_cuerpo(monto: str, moneda: Optional[str]) -> tuple[str, str]:
    """
    Texto para tabla/cuerpo: numero formateado VE + una sola moneda.
    Si no se puede parsear, devuelve texto normalizado sin duplicar BS/USD.
    """
    raw = _normalize_monto_display(monto)
    up = raw.upper()
    num = _parse_numero_desde_texto_monto(raw)
    sym = _etiqueta_moneda(moneda, up)
    if num is not None:
        return _formato_monto_venezolano(num), sym
    # Fallback: quitar tokens de moneda del final y mostrar + simbolo una vez
    import re

    t = (raw or "").strip()
    t = re.sub(r"\s*(BS\.?|USD|USDT)\s*$", "", t, flags=re.IGNORECASE).strip()
    return (t or "-"), sym


def _append_comprobante_adjunto_recibo(
    story: List[Any],
    *,
    _content_w: float,
    section_style: Any,
    comprobante_bytes: Optional[bytes],
    comprobante_tipo: Optional[str],
    comprobante_nombre: Optional[str],
) -> None:
    """
    Incrusta en el PDF la imagen guardada en BD (pagos_reportados.comprobante) cuando es raster.
    Si el archivo es PDF, solo se anade nota (ReportLab no incrusta PDF aqui).
    """
    if not comprobante_bytes or len(comprobante_bytes) < 12:
        return
    from io import BytesIO

    from reportlab.lib.units import inch
    from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table, TableStyle

    ct = (comprobante_tipo or "").lower()
    is_pdf = "pdf" in ct or comprobante_bytes[:5] == b"%PDF-"
    name_esc = html.escape((comprobante_nombre or "").strip()[:160]) if (comprobante_nombre or "").strip() else ""

    if is_pdf:
        story.append(Paragraph("Comprobante digital (PDF)", section_style))
        if name_esc:
            story.append(
                Paragraph(
                    f'<font size="8" color="#64748b">Archivo registrado en sistema: {name_esc}</font>',
                    section_style,
                )
            )
        else:
            story.append(
                Paragraph(
                    '<font size="8" color="#64748b">Copia digital disponible en el sistema (PDF).</font>',
                    section_style,
                )
            )
        story.append(Spacer(1, 12))
        return

    try:
        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(comprobante_bytes))
        pil.load()
        if pil.mode in ("RGBA", "P", "PA"):
            pil = pil.convert("RGB")
        elif pil.mode != "RGB" and pil.mode != "L":
            pil = pil.convert("RGB")
        normalized = BytesIO()
        pil.save(normalized, format="PNG", optimize=True)
        normalized.seek(0)
        im = RLImage(normalized)
        im._restrictSize(_content_w * 0.92, 4.8 * inch)
        story.append(Paragraph("Imagen del comprobante", section_style))
        if name_esc:
            story.append(
                Paragraph(
                    f'<font size="8" color="#64748b">{name_esc}</font>',
                    section_style,
                )
            )
        story.append(Spacer(1, 6))
        wrap = Table([[im]], colWidths=[_content_w])
        wrap.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(wrap)
        story.append(Spacer(1, 14))
    except Exception:
        logger.warning(
            "Recibo Cobros: no se pudo embeber comprobante como imagen (tipo=%s, bytes=%s)",
            (comprobante_tipo or "")[:80],
            len(comprobante_bytes),
            exc_info=True,
        )


def _cedula_display(tipo_cedula: str, numero_cedula: str) -> str:
    tipo = (tipo_cedula or "").strip().upper()
    numero = (numero_cedula or "").strip().upper().replace("-", "").replace(" ", "")
    if tipo and numero.startswith(tipo):
        numero = numero[len(tipo):]
    return f"{tipo}-{numero}".strip("-")


def generar_recibo_pago_reportado(
    referencia_interna: str,
    nombres: str,
    apellidos: str,
    tipo_cedula: str,
    numero_cedula: str,
    institucion_financiera: str,
    monto: str,
    numero_operacion: str,
    fecha_recepcion: Optional[object] = None,
    fecha_pago: Optional[date] = None,
    fecha_reporte_aprobacion_display: Optional[str] = None,
    aplicado_a_cuotas: Optional[str] = None,
    saldo_inicial: Optional[str] = None,
    saldo_final: Optional[str] = None,
    numero_cuota: Optional[int] = None,
    fecha_pago_display: Optional[str] = None,
    moneda: Optional[str] = None,
    tasa_cambio: Optional[float] = None,
    estado_cuota: Optional[str] = None,
    comprobante_bytes: Optional[bytes] = None,
    comprobante_tipo: Optional[str] = None,
    comprobante_nombre: Optional[str] = None,
) -> bytes:
    """Genera el PDF del recibo con datos reales del pago reportado."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    del fecha_recepcion  # No se usa en plantilla; ver fecha_reporte_aprobacion_display.

    # Paleta corporativa (documento formal)
    _c = {
        "ink": colors.HexColor("#0f172a"),
        "muted": colors.HexColor("#64748b"),
        "subtle": colors.HexColor("#475569"),
        "border": colors.HexColor("#e2e8f0"),
        "border_strong": colors.HexColor("#cbd5e1"),
        "row_alt": colors.HexColor("#f8fafc"),
        "row_white": colors.white,
        "accent": colors.HexColor("#0d9488"),
        "accent_dark": colors.HexColor("#115e59"),
        "panel": colors.HexColor("#f1f5f9"),
        "table_head": colors.HexColor("#1e293b"),
    }

    # Saldos del abono
    saldo_init_display = (saldo_inicial or "").strip() or "-"
    saldo_fin_display = (saldo_final or "").strip() or "-"
    cuota_num_display = f"Cuota {numero_cuota}" if numero_cuota else "-"

    fecha_reporte_str = (fecha_reporte_aprobacion_display or "").strip() or fecha_hoy_caracas().strftime(
        "%d/%m/%Y"
    )
    fecha_pago_str = fecha_pago.strftime("%d/%m/%Y") if fecha_pago else "-"

    nombre_completo = f"{(nombres or '').strip()} {(apellidos or '').strip()}".strip()
    cedula = _cedula_display(tipo_cedula, numero_cedula)
    banco = (institucion_financiera or "").strip()
    banco_valido = "" if _is_placeholder_text(banco) else banco
    numero_op = (numero_operacion or "").strip()
    cuotas_txt = (aplicado_a_cuotas or "").strip() or RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE
    estado_cuota_lbl = ((estado_cuota or "").strip() or None)

    monto_ve, moneda_sym = _monto_tabla_y_cuerpo(monto, moneda)
    monto_display = f"{monto_ve} {moneda_sym}" if monto_ve != "-" else "-"
    moneda_symbol = moneda_sym

    buf = io.BytesIO()
    _content_w = letter[0] - 1.3 * inch
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.55 * inch,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    doc_kind_style = ParagraphStyle(
        "ReceiptDocKind",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=_c["ink"],
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=8,
    )
    ref_style = ParagraphStyle(
        "ReceiptRef",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=_c["accent_dark"],
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    company_fallback_style = ParagraphStyle(
        "ReceiptCompanyFallback",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=_c["ink"],
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "ReceiptSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=_c["table_head"],
        alignment=TA_LEFT,
        spaceBefore=4,
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=_c["muted"],
        fontName="Helvetica-Bold",
        splitLongWords=0,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=_c["ink"],
        fontName="Helvetica",
    )
    value_emphasis_style = ParagraphStyle(
        "ValueEmphasis",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=14,
        textColor=_c["ink"],
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=_c["ink"],
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
    )
    footer_title_style = ParagraphStyle(
        "FooterTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=_c["table_head"],
        spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=_c["subtle"],
        fontName="Helvetica",
    )
    saldo_head_style = ParagraphStyle(
        "SaldoHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    saldo_cell_style = ParagraphStyle(
        "SaldoCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=_c["ink"],
        alignment=TA_RIGHT,
        fontName="Helvetica",
    )
    saldo_cell_center_style = ParagraphStyle(
        "SaldoCellCtr",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=_c["ink"],
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    story = []
    ref_display = _referencia_display(referencia_interna)

    # Cabecera centrada (membrete)
    if _LOGO_PATH.exists():
        _logo = Image(str(_LOGO_PATH), width=1.35 * inch, height=1.35 * inch)
        _logo_tbl = Table([[_logo]], colWidths=[_content_w])
        _logo_tbl.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(_logo_tbl)
    else:
        story.append(Paragraph("<b>RapiCredit C.A.</b>", company_fallback_style))

    story.append(Paragraph("COMPROBANTE DE PAGO", doc_kind_style))
    story.append(Paragraph(f"Nro. {ref_display}", ref_style))

    _accent = Table([[""]], colWidths=[_content_w], rowHeights=[3])
    _accent.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _c["accent"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(_accent)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Datos del comprobante", section_style))

    info = [
        [
            Paragraph("Fecha de reporte de pago", label_style),
            Paragraph(fecha_reporte_str, value_style),
            Paragraph("FECHA DE PAGO", label_style),
            Paragraph(fecha_pago_str, value_style),
        ],
        [
            Paragraph("TITULAR", label_style),
            Paragraph(nombre_completo or "-", value_style),
            Paragraph("", label_style),
            Paragraph("", label_style),
        ],
        [
            Paragraph("BANCO", label_style),
            Paragraph(banco_valido or "-", value_style),
            Paragraph("OPERACIÓN", label_style),
            Paragraph(numero_op or "-", value_style),
        ],
        [
            Paragraph("Monto pagado", label_style),
            Paragraph(f"<b>{monto_display}</b>", value_emphasis_style),
            Paragraph("", label_style),
            Paragraph("", label_style),
        ],
        [
            Paragraph("APLICADO A", label_style),
            Paragraph(f"<b>{cuotas_txt}</b>", value_emphasis_style),
            Paragraph("", label_style),
            Paragraph("", value_style),
        ],
    ]

    _info_style = [
        ("BOX", (0, 0), (-1, -1), 1, _c["border_strong"]),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_c["row_white"], _c["row_alt"]]),
        ("GRID", (0, 0), (-1, -1), 0.35, _c["border"]),
        ("SPAN", (1, 1), (3, 1)),
        ("SPAN", (1, 3), (3, 3)),
        ("SPAN", (1, 4), (3, 4)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]

    # Etiquetas (cols 0 y 2): ancho suficiente para no partir palabras largas (fecha de reporte, monto pagado, etc.).
    # Col 3: valores largos (número de operación) pueden partirse; col 1: titular.
    _info_col_w = [
        _content_w * 0.20,
        _content_w * 0.28,
        _content_w * 0.20,
        _content_w * 0.32,
    ]
    table = Table(info, colWidths=_info_col_w)
    table.setStyle(TableStyle(_info_style))

    story.append(table)
    story.append(Spacer(1, 18))

    _append_comprobante_adjunto_recibo(
        story,
        _content_w=_content_w,
        section_style=section_style,
        comprobante_bytes=comprobante_bytes,
        comprobante_tipo=comprobante_tipo,
        comprobante_nombre=comprobante_nombre,
    )

    # Tabla de saldos si hay cuota
    if numero_cuota:
        fecha_pago_col = (fecha_pago_display or "").strip() or "-"
        _estado_cell = estado_cuota_lbl or "-"
        saldos_table = Table(
            [
                [
                    Paragraph("CUOTA", saldo_head_style),
                    Paragraph("SALDO INICIAL", saldo_head_style),
                    Paragraph("ABONO", saldo_head_style),
                    Paragraph("FECHA PAGO", saldo_head_style),
                    Paragraph("SALDO FINAL", saldo_head_style),
                    Paragraph("ESTADO", saldo_head_style),
                ],
                [
                    Paragraph(f"<b>{cuota_num_display}</b>", saldo_cell_center_style),
                    Paragraph(_celda_monto_con_simbolo(saldo_init_display, moneda_symbol), saldo_cell_style),
                    Paragraph(
                        f"<b>{monto_display}</b>" if monto_display != "-" else "-",
                        saldo_cell_style,
                    ),
                    Paragraph(fecha_pago_col, saldo_cell_center_style),
                    Paragraph(_celda_monto_con_simbolo(saldo_fin_display, moneda_symbol), saldo_cell_style),
                    Paragraph(_estado_cell, saldo_cell_center_style),
                ],
            ],
            colWidths=[0.62 * inch, 1.02 * inch, 1.02 * inch, 1.0 * inch, 1.02 * inch, 1.12 * inch],
        )
        saldos_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, _c["border_strong"]),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                ("BACKGROUND", (0, 0), (-1, 0), _c["table_head"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, 1), [_c["row_white"]]),
                ("GRID", (0, 0), (-1, -1), 0.35, _c["border"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(Paragraph("Desglose del abono", section_style))
        story.append(Spacer(1, 4))
        story.append(saldos_table)
        story.append(Spacer(1, 18))

    moneda_u = (moneda or "").strip().upper()
    if not moneda_u and moneda_sym == "Bs.":
        moneda_u = "BS"

    if banco_valido:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{nombre_completo or '-'}</b> (cedula <b>{cedula or '-'}</b>). "
            f"El pago fue reportado por <b>{monto_display or '-'}</b> en la institucion "
            f"<b>{banco_valido}</b>, con numero de operacion <b>{numero_op or '-'}</b>."
        )
    else:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{nombre_completo or '-'}</b> (cedula <b>{cedula or '-'}</b>). "
            f"El pago fue reportado por <b>{monto_display or '-'}</b>, "
            f"con numero de operacion <b>{numero_op or '-'}</b>."
        )
    if aplicado_a_cuotas and (aplicado_a_cuotas or "").strip():
        cuerpo += (
            f" Este comprobante corresponde al abono registrado a <b>{(aplicado_a_cuotas or '').strip()}</b> "
            "del credito, segun la tabla de amortizacion."
        )
    else:
        cuerpo += (
            f" <b>{RECIBO_TEXTO_CUOTA_EN_REVISION_CLIENTE}</b>: el pago fue recibido y esta en proceso de "
            "verificacion y conciliacion antes de aplicarse a la tabla de amortizacion."
        )
    if moneda_u == "USD":
        cuerpo += (
            " Monto indicado en <b>USD</b> (dolares estadounidenses)."
        )
    elif moneda_u == "BS" and tasa_cambio is not None:
        tasa_txt = _formato_decimal_ve(float(tasa_cambio))
        cuerpo += (
            f" Monto en <b>bolivares (Bs.)</b>. Tasa de cambio oficial para la fecha de pago "
            f"(<b>{fecha_pago_str}</b>): <b>{tasa_txt}</b> Bs. por 1 USD."
        )
    _narrative = Table([[Paragraph(cuerpo, body_style)]], colWidths=[_content_w])
    _narrative.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _c["panel"]),
                ("BOX", (0, 0), (-1, -1), 0.75, _c["border"]),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(_narrative)
    story.append(Spacer(1, 22))

    _foot = Table(
        [
            [Paragraph("Contacto de cobranza", footer_title_style)],
            [Paragraph(f"Correo: <a color='#0d9488' href='mailto:{CONTACTO_COBRANZA}'>{CONTACTO_COBRANZA}</a>", footer_style)],
            [Paragraph(f'WhatsApp: <a color="#0d9488" href="{WHATSAPP_LINK}">{WHATSAPP_DISPLAY}</a>', footer_style)],
        ],
        colWidths=[_content_w],
    )
    _foot.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, _c["accent"]),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(_foot)

    doc.build(story)
    return buf.getvalue()
