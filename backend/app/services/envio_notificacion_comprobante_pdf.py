"""Genera PDF de comprobante de envio (informacion legal + metadatos SMTP capturados en el envio)."""

from __future__ import annotations

import io
import json
import logging
import os
from xml.sax.saxutils import escape
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from app.models.envio_notificacion import EnvioNotificacion

logger = logging.getLogger(__name__)

_LEGAL_PRUEBA_SMTP = (
    "ACLARACION PARA FINES DE COBRANZA Y PROCESALES: Este PDF documenta el registro en el sistema "
    "RapiCredit del envio de correo electronico. Cuando el resultado SMTP figura como "
    "\"aceptado_por_servidor_smtp\", significa que el servidor de salida configurado (relay) "
    "acepto el mensaje en la sesion SMTP para entregarlo hacia los destinatarios indicados, sin rechazo "
    "inmediato en esa sesion. Eso no prueba que el destinatario haya recibido, leido o conservado el "
    "correo en su buzon, ni excluye filtros de spam o demoras. La IP indicada como servidor SMTP es "
    "la del primer salto (conexion del sistema al proveedor de correo), no la del buzon final del "
    "destinatario (dato no disponible mediante SMTP estandar). La IP del socket local corresponde al "
    "extremo de la conexion en el servidor de aplicacion (a menudo una IP interna; la IP publica de "
    "salida depende del proveedor de hosting). Si el resultado es fallo o rechazo, no hubo aceptacion "
    "completa segun el registro capturado."
)


def _font_name_comprobante() -> str:
    try:
        import reportlab

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        fonts_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
        vera = os.path.join(fonts_dir, "Vera.ttf")
        if os.path.isfile(vera):
            if "VeraComprobante" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("VeraComprobante", vera))
            return "VeraComprobante"
    except Exception as e:
        logger.warning("[COMPROBANTE_PDF] fuente Vera no registrada: %s", e)
    return "Helvetica"


def _meta_get(meta: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not meta or not isinstance(meta, dict):
        return default
    v = meta.get(key)
    if v is None:
        return default
    if isinstance(v, (list, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)[:1500]
        except (TypeError, ValueError):
            return str(v)[:1500]
    return str(v)


def generar_comprobante_envio_pdf_bytes(envio: "EnvioNotificacion") -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        logger.warning("[COMPROBANTE_PDF] reportlab no disponible: %s", e)
        return None

    font = _font_name_comprobante()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ComprobanteTitle",
        parent=styles["Title"],
        fontName=font,
        fontSize=14,
        leading=18,
    )
    heading_style = ParagraphStyle(
        name="ComprobanteH2",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=11,
        leading=14,
    )
    cell_label_style = ParagraphStyle(
        name="ComprobanteCellLabel",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        leading=10,
    )
    cell_value_style = ParagraphStyle(
        name="ComprobanteCellValue",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        leading=10,
    )
    legal_style = ParagraphStyle(
        name="ComprobanteLegal",
        parent=styles["Normal"],
        fontName=font,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#333333"),
    )
    footer_style = ParagraphStyle(
        name="ComprobanteFooter",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#666666"),
    )

    def pc(text: str, style) -> Paragraph:
        return Paragraph(escape(str(text if text is not None else "")), style)

    meta_raw = getattr(envio, "metadata_tecnica", None)
    meta: Optional[Dict[str, Any]] = meta_raw if isinstance(meta_raw, dict) else None

    asunto = getattr(envio, "asunto", None) or (
        f"Notificaci\u00f3n {envio.tipo_tab}" if envio.tipo_tab else "Env\u00edo"
    )
    if envio.exito:
        estado_registro = "Exito: servidor SMTP acepto el mensaje (relay)"
    else:
        estado_registro = "Fallo o rechazo: no consta aceptacion SMTP completa"

    fecha = envio.fecha_envio.isoformat() if envio.fecha_envio else ""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        title=f"Comprobante env\u00edo #{envio.id}",
        leftMargin=50,
        rightMargin=50,
    )
    story: List[Any] = [
        pc("Comprobante de env\u00edo de notificaci\u00f3n (PDF oficial)", title_style),
        Spacer(1, 10),
        Paragraph(
            "<b>ID registro:</b> " + escape(str(envio.id)),
            cell_value_style,
        ),
        Spacer(1, 12),
        pc("Datos del env\u00edo", heading_style),
        Spacer(1, 6),
    ]

    datos_envio: List[Tuple[str, str]] = [
        ("Fecha / hora registro (BD)", fecha),
        ("Tipo (pestana / caso)", envio.tipo_tab or ""),
        ("Asunto", asunto),
        ("Destinatario (email)", envio.email or ""),
        ("Nombre", envio.nombre or ""),
        ("C\u00e9dula", envio.cedula or ""),
        ("Estado en este comprobante", estado_registro),
        ("Error registrado (si aplica)", (envio.error_mensaje or "")[:2000]),
        ("ID Pr\u00e9stamo", str(envio.prestamo_id or "")),
        ("Correlativo", str(envio.correlativo or "")),
    ]
    t1 = Table(
        [[pc(a, cell_label_style), pc(b, cell_value_style)] for a, b in datos_envio],
        colWidths=[130, 390],
    )
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t1)

    story.append(Spacer(1, 14))
    story.append(pc("Datos t\u00e9cnicos capturados al enviar (SMTP)", heading_style))
    story.append(Spacer(1, 6))

    if meta:
        tecnicos: List[Tuple[str, str]] = [
            ("Message-ID (cabecera RFC 5322)", _meta_get(meta, "message_id_rfc5322")),
            ("Resultado capturado", _meta_get(meta, "resultado")),
            ("Fecha/hora registro t\u00e9cnico (UTC)", _meta_get(meta, "fecha_registro_utc")),
            ("Servidor SMTP (host)", _meta_get(meta, "servidor_smtp_host")),
            ("Servidor SMTP (puerto)", _meta_get(meta, "servidor_smtp_puerto")),
            ("Tipo conexi\u00f3n", _meta_get(meta, "tipo_conexion")),
            ("TLS activo", _meta_get(meta, "tls")),
            (
                "IP servidor SMTP (primer salto; peer de la conexi\u00f3n)",
                _meta_get(meta, "ip_servidor_smtp_conectado"),
            ),
            (
                "Puerto servidor SMTP (peer)",
                _meta_get(meta, "puerto_servidor_smtp_conectado"),
            ),
            (
                "IP socket local (proceso; suele ser interna)",
                _meta_get(meta, "ip_socket_local_proceso"),
            ),
            ("Puerto socket local", _meta_get(meta, "puerto_socket_local")),
            ("Modo pruebas (redirecci\u00f3n)", _meta_get(meta, "modo_pruebas_redirigido")),
            ("Destinatarios en sesi\u00f3n SMTP", _meta_get(meta, "destinatarios_sesion_smtp")),
            ("Detalle rechazo SMTP", _meta_get(meta, "smtp_refused")),
            ("Resumen error", _meta_get(meta, "error_resumen")),
            ("Motivo (sin intento)", _meta_get(meta, "motivo")),
        ]
        tecnicos_filtrados = [(a, b) for a, b in tecnicos if (b or "").strip()]
        if not tecnicos_filtrados:
            tecnicos_filtrados = [
                (
                    "Nota",
                    "Metadatos presentes pero sin campos con valor legible.",
                )
            ]
        t2 = Table(
            [[pc(a, cell_label_style), pc(b, cell_value_style)] for a, b in tecnicos_filtrados],
            colWidths=[130, 390],
        )
    else:
        t2 = Table(
            [
                [
                    pc("Metadatos", cell_label_style),
                    pc(
                        "No hay metadatos t\u00e9cnicos almacenados (env\u00edo anterior a esta versi\u00f3n "
                        "o generaci\u00f3n regenerada sin sesi\u00f3n SMTP).",
                        cell_value_style,
                    ),
                ]
            ],
            colWidths=[130, 390],
        )
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f4ea")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t2)

    story.append(Spacer(1, 14))
    story.append(pc("Alcance probatorio", heading_style))
    story.append(Spacer(1, 6))
    story.append(pc(_LEGAL_PRUEBA_SMTP, legal_style))
    story.append(Spacer(1, 16))
    story.append(
        pc(
            "Documento generado para fines administrativos y legales. RapiCredit.",
            footer_style,
        )
    )
    doc.build(story)
    return buf.getvalue()
