"""Genera PDF de comprobante de envío (misma información que el HTML de historial)."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.envio_notificacion import EnvioNotificacion

logger = logging.getLogger(__name__)


def generar_comprobante_envio_pdf_bytes(envio: "EnvioNotificacion") -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        logger.warning("[COMPROBANTE_PDF] reportlab no disponible: %s", e)
        return None

    asunto = getattr(envio, "asunto", None) or (
        f"Notificación {envio.tipo_tab}" if envio.tipo_tab else "Envío"
    )
    estado_txt = "Entregado" if envio.exito else "Rebotado"
    fecha = envio.fecha_envio.isoformat() if envio.fecha_envio else ""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"Comprobante envío #{envio.id}")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Comprobante de envío de notificación", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>ID registro:</b> {envio.id}", styles["Normal"]),
        Spacer(1, 8),
    ]
    data = [
        ["Fecha envío", fecha],
        ["Tipo", envio.tipo_tab or ""],
        ["Asunto", asunto],
        ["Destinatario (email)", envio.email or ""],
        ["Nombre", envio.nombre or ""],
        ["Cédula", envio.cedula or ""],
        ["Estado", estado_txt],
        ["Error (si aplica)", (envio.error_mensaje or "")[:2000]],
        ["ID Préstamo", str(envio.prestamo_id or "")],
        ["Correlativo", str(envio.correlativo or "")],
    ]
    t = Table(data, colWidths=[140, 380])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Documento generado para fines administrativos y legales. RapiCredit.",
            styles["Normal"],
        )
    )
    doc.build(story)
    return buf.getvalue()
