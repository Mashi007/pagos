"""
Generación del recibo PDF para reportes de pago (módulo Cobros).
Logo RapiCredit, cuerpo del recibo, número de referencia, pie con contacto y WhatsApp.
Incluye fecha de emisión del recibo y fecha de pago (desde tabla pagos_reportados).
"""
import io
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# WhatsApp RapiCredit: 424-4579934 — https://wa.me/584244579934 (usado en recibo, rechazos y confirmaciones)
WHATSAPP_LINK = "https://wa.me/584244579934"
WHATSAPP_DISPLAY = "424-4579934"
CONTACTO_COBRANZA = "cobranza@rapicreditca.com"

# Ruta al logo: backend/static/logo.png (desde app/services/cobros/ subimos a backend)
_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo.png"


def generar_recibo_pago_reportado(
    referencia_interna: str,
    nombres: str,
    apellidos: str,
    tipo_cedula: str,
    numero_cedula: str,
    institucion_financiera: str,
    monto: str,
    numero_operacion: str,
    fecha_recepcion: Optional[datetime] = None,
    fecha_pago: Optional[date] = None,
) -> bytes:
    """
    Genera el PDF del recibo de reporte de pago.
    Cabecera: logo (imagen si existe) y texto "RapiCredit C.A.".
    Cuerpo: mensaje estándar con datos del reporte.
    Fechas: fecha de emisión del recibo (recepción) y fecha de pago (desde pagos_reportados).
    Pie: datos de contacto y WhatsApp clickeable (en PDF como URL).
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Center", alignment=1))
    styles.add(ParagraphStyle(name="Small", fontSize=9, spaceAfter=4))

    fecha_emision = fecha_recepcion or datetime.utcnow()
    fecha_emision_str = fecha_emision.strftime("%d/%m/%Y %H:%M")
    fecha_pago_str = fecha_pago.strftime("%d/%m/%Y") if fecha_pago else "—"

    story = []
    # Cabecera: logo RapiCredit si existe, luego texto
    if _LOGO_PATH.exists():
        logo_img = Image(str(_LOGO_PATH), width=2.0 * inch, height=2.0 * inch)
        story.append(logo_img)
        story.append(Spacer(1, 8))
    story.append(Paragraph("<b>RapiCredit C.A.</b>", styles["Title"]))
    story.append(Paragraph(f"Recibo de pago — {referencia_interna}", styles["Heading2"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Fecha de emisión del recibo:</b> {fecha_emision_str}", styles["Normal"]))
    story.append(Paragraph(f"<b>Fecha de pago:</b> {fecha_pago_str}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Cuerpo
    nombre_completo = f"{nombres} {apellidos}".strip()
    cedula_display = f"{tipo_cedula}-{numero_cedula}"
    cuerpo = (
        f'Se ha recibido reporte de pago de la Sra./Sr. <b>{nombre_completo}</b>, '
        f'titular de la cédula <b>{cedula_display}</b>, proveniente del banco <b>{institucion_financiera}</b>, '
        f'por la cantidad de <b>{monto}</b> Bs., con número de operación <b>{numero_operacion}</b>.'
    )
    story.append(Paragraph(cuerpo, styles["Normal"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f"<b>Número de referencia:</b> {referencia_interna}", styles["Normal"]))
    story.append(Spacer(1, 24))

    # Pie: contacto y WhatsApp (en PDF el enlace se puede hacer clickeable)
    story.append(Paragraph("<b>Datos de contacto — RapiCredit C.A.</b>", styles["Normal"]))
    story.append(Paragraph(f"Email: {CONTACTO_COBRANZA}", styles["Small"]))
    story.append(Paragraph(
        f'WhatsApp: <a href="{WHATSAPP_LINK}">{WHATSAPP_DISPLAY}</a>',
        styles["Small"],
    ))

    doc.build(story)
    return buf.getvalue()