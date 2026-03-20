"""
Generacion del recibo PDF para reportes de pago (modulo Cobros).
Diseno profesional con encabezado, resumen estructurado y bloque narrativo.
"""
import io
from datetime import date
from pathlib import Path
from typing import Optional

WHATSAPP_LINK = "https://wa.me/584244579934"
WHATSAPP_DISPLAY = "424-4579934"
CONTACTO_COBRANZA = "cobranza@rapicreditca.com"

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"


def _referencia_display(referencia_interna: str) -> str:
    ref = (referencia_interna or "").strip()
    if not ref:
        return "-"
    return ref if ref.startswith("#") else f"#{ref}"


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
) -> bytes:
    """Genera el PDF del recibo con datos reales del pago reportado."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    del fecha_recepcion  # No se usa: la emision del recibo es la fecha actual.

    fecha_emision_str = date.today().strftime("%d/%m/%Y")
    fecha_pago_str = fecha_pago.strftime("%d/%m/%Y") if fecha_pago else "-"

    nombre_completo = f"{(nombres or '').strip()} {(apellidos or '').strip()}".strip()
    cedula = _cedula_display(tipo_cedula, numero_cedula)
    banco = (institucion_financiera or "").strip()
    monto_display = (monto or "").strip()
    numero_op = (numero_operacion or "").strip()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#64748b"),
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#0f172a"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10.2,
        leading=15,
        textColor=colors.HexColor("#111827"),
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
    )

    story = []

    if _LOGO_PATH.exists():
        story.append(Image(str(_LOGO_PATH), width=1.45 * inch, height=1.45 * inch))
        story.append(Spacer(1, 6))

    story.append(Paragraph("<b>RapiCredit C.A.</b>", title_style))
    ref_display = _referencia_display(referencia_interna)
    story.append(Paragraph(f"Recibo de pago Nro. {ref_display}", subtitle_style))

    info = [
        [Paragraph("Fecha de emision", label_style), Paragraph(fecha_emision_str, value_style), Paragraph("Fecha de pago", label_style), Paragraph(fecha_pago_str, value_style)],
        [Paragraph("Titular", label_style), Paragraph(nombre_completo or "-", value_style), Paragraph("Cedula", label_style), Paragraph(cedula or "-", value_style)],
        [Paragraph("Banco", label_style), Paragraph(banco or "-", value_style), Paragraph("Operacion", label_style), Paragraph(numero_op or "-", value_style)],
        [Paragraph("Monto reportado", label_style), Paragraph(f"<b>{monto_display or '-'}</b>", value_style), Paragraph("Referencia", label_style), Paragraph(ref_display, value_style)],
    ]

    table = Table(info, colWidths=[1.45 * inch, 2.0 * inch, 1.2 * inch, 1.45 * inch])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 12))

    cuerpo = (
        "Se confirma la recepcion de su reporte de pago, asociado al titular "
        f"<b>{nombre_completo or '-'}</b> (cedula <b>{cedula or '-'}</b>). "
        f"El pago fue reportado por <b>{monto_display or '-'}</b> en la institucion "
        f"<b>{banco or '-'}</b>, con numero de operacion <b>{numero_op or '-'}</b>."
    )
    story.append(Paragraph(cuerpo, body_style))
    story.append(Spacer(1, 18))

    story.append(Paragraph("<b>Contacto de cobranza</b>", value_style))
    story.append(Paragraph(f"Email: {CONTACTO_COBRANZA}", footer_style))
    story.append(Paragraph(f'WhatsApp: <a href="{WHATSAPP_LINK}">{WHATSAPP_DISPLAY}</a>', footer_style))

    doc.build(story)
    return buf.getvalue()
