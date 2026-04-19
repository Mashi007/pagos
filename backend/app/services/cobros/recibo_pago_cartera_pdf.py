"""
Recibo PDF por pago de cartera (tabla pagos, estado PAGADO).
Enfasis: monto reconocido/aprobado en cartera.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from app.services.cobros.recibo_pdf import (
    CONTACTO_COBRANZA,
    WHATSAPP_DISPLAY,
    WHATSAPP_LINK,
    _append_comprobante_adjunto_recibo,
    pie_pagina_recibo_centrada,
)
_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"


def generar_recibo_pago_cartera_pdf(
    *,
    referencia_documento: str,
    fecha_reporte_aprobacion_display: str,
    fecha_pago_display: str,
    titular_credito: str,
    cedula_titular: str,
    cedula_comprobante: str,
    banco: str,
    numero_operacion: str,
    monto_pagado_texto: str,
    nota_tasa_bs: Optional[str] = None,
    comprobante_bytes: Optional[bytes] = None,
    comprobante_tipo: Optional[str] = None,
    comprobante_nombre: Optional[str] = None,
) -> bytes:
    """Comprobante de pago reconocido en cartera (sin tabla de desglose por cuota)."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
        "table_head": colors.HexColor("#1e293b"),
    }

    buf = io.BytesIO()
    _content_w = letter[0] - 1.3 * inch
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
    )
    styles = getSampleStyleSheet()

    doc_kind_style = ParagraphStyle(
        "CarteraDoc",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=_c["ink"],
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=6,
    )
    ref_style = ParagraphStyle(
        "CarteraRef",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=_c["accent_dark"],
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "CarteraSec",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=_c["table_head"],
        alignment=TA_LEFT,
        spaceBefore=6,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "CarteraLbl",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=_c["muted"],
        fontName="Helvetica-Bold",
        splitLongWords=0,
    )
    value_style = ParagraphStyle(
        "CarteraVal",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=_c["ink"],
        fontName="Helvetica",
    )
    body_style = ParagraphStyle(
        "CarteraBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        textColor=_c["ink"],
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
    )
    story = []
    if _LOGO_PATH.exists():
        logo = Image(str(_LOGO_PATH), width=1.2 * inch, height=1.2 * inch)
        lt = Table([[logo]], colWidths=[_content_w])
        lt.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(lt)

    story.append(Paragraph("COMPROBANTE DE PAGO", doc_kind_style))
    story.append(Paragraph(f"Ref. {referencia_documento}", ref_style))
    story.append(Spacer(1, 10))

    info = [
        [
            Paragraph("Fecha de reporte de pago", label_style),
            Paragraph(fecha_reporte_aprobacion_display or "-", value_style),
            Paragraph("FECHA DE PAGO", label_style),
            Paragraph(fecha_pago_display or "-", value_style),
        ],
        [
            Paragraph("TITULAR DEL CREDITO", label_style),
            Paragraph(titular_credito or "-", value_style),
            Paragraph("CEDULA TITULAR", label_style),
            Paragraph(cedula_titular or "-", value_style),
        ],
        [
            Paragraph("CEDULA EN COMPROBANTE", label_style),
            Paragraph(cedula_comprobante or "-", value_style),
            Paragraph("", label_style),
            Paragraph("", label_style),
        ],
        [
            Paragraph("BANCO / INSTITUCION", label_style),
            Paragraph(banco or "-", value_style),
            Paragraph("NÚMERO DE DOCUMENTO", label_style),
            Paragraph(numero_operacion or "-", value_style),
        ],
        [
            Paragraph("MONTO PAGADO (RECONOCIDO)", label_style),
            Paragraph(f"<b>{monto_pagado_texto}</b>", value_style),
            Paragraph("", label_style),
            Paragraph("", label_style),
        ],
    ]
    _info_style = [
        ("BOX", (0, 0), (-1, -1), 1, _c["border_strong"]),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_c["row_white"], _c["row_alt"]]),
        ("GRID", (0, 0), (-1, -1), 0.35, _c["border"]),
        ("SPAN", (1, 2), (3, 2)),
        ("SPAN", (1, 4), (3, 4)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]
    colw = [_content_w * 0.20, _content_w * 0.28, _content_w * 0.20, _content_w * 0.32]
    story.append(Table(info, colWidths=colw))
    story[-1].setStyle(TableStyle(_info_style))
    story.append(Spacer(1, 14))
    if (nota_tasa_bs or "").strip():
        story.append(Paragraph((nota_tasa_bs or "").strip(), body_style))
        story.append(Spacer(1, 10))

    _append_comprobante_adjunto_recibo(
        story,
        _content_w=_content_w,
        section_style=section_style,
        comprobante_bytes=comprobante_bytes,
        comprobante_tipo=comprobante_tipo,
        comprobante_nombre=comprobante_nombre,
    )

    foot = Table(
        [
            [Paragraph("Contacto de cobranza", section_style)],
            [
                Paragraph(
                    f"Correo: <a color='#0d9488' href='mailto:{CONTACTO_COBRANZA}'>{CONTACTO_COBRANZA}</a>",
                    body_style,
                )
            ],
            [
                Paragraph(
                    f'WhatsApp: <a color="#0d9488" href="{WHATSAPP_LINK}">{WHATSAPP_DISPLAY}</a>',
                    body_style,
                )
            ],
        ],
        colWidths=[_content_w],
    )
    foot.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, _c["accent"]),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
            ]
        )
    )
    story.append(Spacer(1, 16))
    story.append(foot)

    doc.build(
        story,
        onFirstPage=pie_pagina_recibo_centrada,
        onLaterPages=pie_pagina_recibo_centrada,
    )
    return buf.getvalue()
