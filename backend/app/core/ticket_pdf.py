"""
Generación de informe PDF para tickets CRM.
Usado al crear un ticket para adjuntar al correo automático.
"""
import io
from datetime import datetime
from typing import Optional


def generar_informe_pdf_ticket(
    ticket_id: int,
    titulo: str,
    descripcion: str,
    cliente_nombre: Optional[str] = None,
    prioridad: str = "media",
    estado: str = "abierto",
    tipo: str = "consulta",
    fecha_creacion: Optional[datetime] = None,
) -> bytes:
    """
    Genera un PDF con el informe del ticket (para adjuntar al email de notificación).
    Usa reportlab (misma dependencia que reportes/cobranzas).
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Informe de ticket — CRM RapiCredit", styles["Title"]))
    story.append(Spacer(1, 12))

    fecha_str = (
        fecha_creacion.strftime("%d/%m/%Y %H:%M")
        if fecha_creacion
        else datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    )

    story.append(Paragraph(f"<b>ID:</b> {ticket_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Título:</b> {titulo or '—'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Estado:</b> {estado or 'abierto'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Prioridad:</b> {prioridad or 'media'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Tipo:</b> {tipo or 'consulta'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Fecha de creación:</b> {fecha_str}", styles["Normal"]))
    if cliente_nombre:
        story.append(Paragraph(f"<b>Cliente:</b> {cliente_nombre}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Descripción</b>", styles["Normal"]))
    # Escapar caracteres problemáticos para reportlab en descripción
    desc_safe = (descripcion or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    story.append(Paragraph(desc_safe or "—", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
