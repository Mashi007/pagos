"""
Generador de Carta de Cobranza en PDF - Rapi-Credit, C.A.
Adjunto automático al email de cobranza. Usa datos del contexto (clientes, préstamos, cuotas).
La plantilla editable se almacena en configuracion con clave 'plantilla_pdf_cobranza' (JSON).
"""
import io
import json
import logging
from datetime import date
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Colores corporativos (script original)
AZUL = "#1E3A6E"
NARANJA = "#E84C0E"
GRIS_TEXTO = "#444444"


def _format_fecha(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            d = date.fromisoformat(value[:10])
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(value)
    return str(value)


def _datos_desde_contexto(contexto: dict, plantilla_override: Optional[dict] = None) -> dict:
    """Convierte contexto_cobranza a la estructura DATOS del PDF (ciudad, fecha_carta, etc.)."""
    plantilla_override = plantilla_override or {}
    cuotas = contexto.get("CUOTAS.VENCIMIENTOS") or contexto.get("cuotas_vencidas") or []
    fechas_cuotas = []
    monto_total = 0
    for c in cuotas:
        fv = c.get("fecha_vencimiento") if isinstance(c, dict) else getattr(c, "fecha_vencimiento", None)
        fechas_cuotas.append(_format_fecha(fv))
        m = c.get("monto") or c.get("monto_cuota") if isinstance(c, dict) else (getattr(c, "monto", None) or getattr(c, "monto_cuota", None))
        if m is not None:
            try:
                monto_total += float(m)
            except (TypeError, ValueError):
                pass
    fecha_carta = contexto.get("FECHA_CARTA")
    return {
        "ciudad": plantilla_override.get("ciudad_default") or "Guacara",
        "fecha_carta": _format_fecha(fecha_carta),
        "notificacion_num": str(contexto.get("PRESTAMOS.ID", "")),
        "tratamiento": contexto.get("CLIENTES.TRATAMIENTO") or "Sr(a).",
        "nombre_completo": contexto.get("CLIENTES.NOMBRE_COMPLETO") or "",
        "cedula": contexto.get("CLIENTES.CEDULA") or "",
        "monto_total_usd": f"{monto_total:.2f}",
        "num_cuotas": str(len(cuotas)),
        "fechas_cuotas": fechas_cuotas,
    }


def _get_plantilla_pdf_config(db=None) -> dict:
    """Carga plantilla editable desde configuracion (clave plantilla_pdf_cobranza)."""
    if db is None:
        return {}
    try:
        from app.models.configuracion import Configuracion
        row = db.get(Configuracion, "plantilla_pdf_cobranza")
        if row and row.valor:
            return json.loads(row.valor)
    except Exception as e:
        logger.warning("No se pudo cargar plantilla_pdf_cobranza: %s", e)
    return {}


def _dict_reemplazo_pdf(contexto: dict, datos: dict) -> dict:
    """
    Construye un diccionario plano para reemplazar variables en la plantilla PDF.
    Incluye claves de datos (monto_total_usd, num_cuotas, fechas_str, etc.) y de contexto
    (CLIENTES.NOMBRE_COMPLETO, FECHA_CARTA, PRESTAMOS.ID, NUMEROCORRELATIVO, TOTAL_ADEUDADO, etc.).
    Todas las variables se sustituyen con datos reales al enviar.
    """
    out = dict(datos)
    fechas_cuotas = datos.get("fechas_cuotas") or []
    out["fechas_str"] = ", ".join(fechas_cuotas)
    # Claves desde contexto (mismo que email cobranza)
    out["CLIENTES.TRATAMIENTO"] = datos.get("tratamiento", "") or contexto.get("CLIENTES.TRATAMIENTO") or "Sr(a)."
    out["CLIENTES.NOMBRE_COMPLETO"] = datos.get("nombre_completo", "") or contexto.get("CLIENTES.NOMBRE_COMPLETO") or ""
    out["CLIENTES.CEDULA"] = datos.get("cedula", "") or contexto.get("CLIENTES.CEDULA") or ""
    out["PRESTAMOS.ID"] = datos.get("notificacion_num", "") or str(contexto.get("PRESTAMOS.ID", ""))
    out["IDPRESTAMO"] = out["PRESTAMOS.ID"]
    out["FECHA_CARTA"] = datos.get("fecha_carta", "") or _format_fecha(contexto.get("FECHA_CARTA"))
    out["NUMEROCORRELATIVO"] = str(contexto.get("NUMEROCORRELATIVO", ""))
    out["TOTAL_ADEUDADO"] = str(contexto.get("TOTAL_ADEUDADO", ""))
    out["LOGO_URL"] = str(contexto.get("LOGO_URL", ""))
    return out


def _reemplazar_variables_plantilla_pdf(texto: Optional[str], contexto: dict, datos: dict) -> str:
    """
    Reemplaza en texto todas las variables {{KEY}} y {KEY} con datos reales del contexto/BD.
    """
    if not texto:
        return ""
    reemplazo = _dict_reemplazo_pdf(contexto, datos)
    result = texto
    for key, value in reemplazo.items():
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)
        result = result.replace("{{" + key + "}}", value).replace("{" + key + "}", value)
    return result


def build_pdf_bytes(
    datos: dict,
    logo_path: Optional[str] = None,
    cuerpo_principal: Optional[str] = None,
    clausula_septima: Optional[str] = None,
) -> bytes:
    """
    Genera el PDF de la carta de cobranza (ReportLab).
    datos: dict con ciudad, fecha_carta, notificacion_num, tratamiento, nombre_completo, cedula,
           monto_total_usd, num_cuotas, fechas_cuotas (list).
    logo_path: ruta al PNG del logo (opcional).
    cuerpo_principal / clausula_septima: textos opcionales (si no se pasan se usan los por defecto).
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    import os

    azul = colors.HexColor(AZUL)
    naranja = colors.HexColor(NARANJA)
    gris = colors.HexColor(GRIS_TEXTO)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    s_fecha = ParagraphStyle("fecha", fontSize=10, textColor=gris, alignment=TA_RIGHT, leading=14)
    s_notif = ParagraphStyle("notif", fontSize=10, textColor=gris, alignment=TA_RIGHT, bold=True, leading=14)
    s_dest = ParagraphStyle("dest", fontSize=11, textColor=azul, fontName="Helvetica-Bold", leading=16)
    s_cedula = ParagraphStyle("ced", fontSize=11, textColor=gris, leading=14)
    s_body = ParagraphStyle("body", fontSize=10.5, textColor=gris, leading=16, alignment=TA_JUSTIFY, spaceAfter=8)
    s_clausula_titulo = ParagraphStyle("ctit", fontSize=10.5, textColor=azul, fontName="Helvetica-Bold", leading=16, alignment=TA_JUSTIFY, spaceAfter=4)
    s_clausula_texto = ParagraphStyle("ctex", fontSize=9.5, textColor=gris, leading=15, alignment=TA_JUSTIFY, leftIndent=40, rightIndent=20)
    s_firma = ParagraphStyle("firma", fontSize=10.5, textColor=azul, fontName="Helvetica-Bold", leading=14)
    s_slogan = ParagraphStyle("slogan", fontSize=10, textColor=naranja, fontName="Helvetica-BoldOblique", leading=14)
    s_footer_empresa = ParagraphStyle("fempresa", fontSize=11, textColor=colors.white, fontName="Helvetica-Bold")
    s_footer_rif = ParagraphStyle("frif", fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")
    s_footer_dir = ParagraphStyle("fdir", fontSize=8, textColor=colors.white, leading=12)

    fechas_str = ", ".join(datos.get("fechas_cuotas") or [])

    story = []

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=5 * cm, height=1.8 * cm)
            logo.hAlign = "LEFT"
            story.append(logo)
        except Exception as e:
            logger.warning("No se pudo cargar logo para PDF cobranza: %s", e)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(f"{datos.get('ciudad', '')}, {datos.get('fecha_carta', '')}", s_fecha))
    story.append(Paragraph(f"<b>Notificación N° {datos.get('notificacion_num', '')}</b>", s_notif))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(f"{datos.get('tratamiento', '')} {datos.get('nombre_completo', '')}", s_dest))
    story.append(Paragraph(datos.get("cedula", ""), s_cedula))
    story.append(Spacer(1, 0.6 * cm))

    _default = (
        "Ante todo, queremos extenderle un cordial saludo, por medio del presente instrumento "
        "queremos recordarle que, a la presente fecha, usted mantiene un saldo pendiente correspondiente a "
        "<b><u>USD {monto_total_usd} ({num_cuotas}) CUOTAS PENDIENTES</u></b> "
        "por cancelación, de fechas: <b>({fechas_str})</b>"
    )
    if cuerpo_principal:
        monto_cuotas_html = cuerpo_principal
    else:
        fechas_str = ", ".join(datos.get("fechas_cuotas") or [])
        monto_cuotas_html = _default.format(
            monto_total_usd=datos.get("monto_total_usd", "0.00"),
            num_cuotas=datos.get("num_cuotas", "0"),
            fechas_str=fechas_str,
        )
    story.append(Paragraph(monto_cuotas_html, s_body))

    p2 = (
        "Recuerde que el pago a tiempo le permite acceder a nuevos beneficios, es por ello, que le "
        "solicitamos realizar el pago de las cuotas pendientes en un lapso no mayor a 48 horas. "
        "<b>De igual manera podrá ver sus cuotas en el Cronograma de Pago y/o Contrato de Reserva de "
        "Dominio suscrito entre las partes.</b>"
    )
    story.append(Paragraph(p2, s_body))
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            "Recordando lo que establece el Contrato de RESERVA DE DOMINIO Suscrito entre partes en su <b>Cláusula Séptima:</b>",
            s_clausula_titulo,
        )
    )
    clausula = clausula_septima or (
        "Es pacto expreso de esta negociación, que el incumplimiento del presente contrato por parte de "
        "<b>EL COMPRADOR (A),</b> y en especial la falta del pago al vencimiento de (2) dos o más cuotas "
        "conforme a los términos establecidos por la Ley, dará derecho a exigir el pago inmediato de la "
        "totalidad del saldo deudor, declarar resuelto de pleno derecho el presente Contrato y recuperar "
        "la propiedad y posesión del bien objeto de esta venta. En caso de devolución <b>EL COMPRADOR (A),</b> "
        "conviene con <b>EL VENDEDOR (A),</b> recoger el vehículo donde se encuentre, sin más avisos ni trámites. "
        "<b>EL COMPRADOR (A),</b> renuncia toda acción que pudiera corresponderle por la recuperación del bien "
        "vehículo, salvo la que la propia ley le acuerde."
    )
    story.append(Paragraph(clausula, s_clausula_texto))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("Agradecemos su pronta atención a este asunto y esperamos su respuesta.", s_body))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Atentamente,", s_body))
    story.append(Spacer(1, 0.8 * cm))

    firma_data = [[
        Paragraph("<b>Departamento Cobranza</b>", s_firma),
        Paragraph("<b>RAPI-CREDIT, C.A.</b><br/>RIF. J-505363506", s_firma),
    ]]
    firma_table = Table(firma_data, colWidths=[8 * cm, 8 * cm])
    firma_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(firma_table)

    slogan_table = Table([[Paragraph("¡Rapidez financiera!", s_slogan), ""]], colWidths=[8 * cm, 8 * cm])
    slogan_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(slogan_table)
    story.append(Spacer(1, 0.8 * cm))

    footer_top = Table([[
        Paragraph("<b>RAPI-CREDIT, C.A</b>", s_footer_empresa),
        Paragraph("<b>J 50536350-6</b>", s_footer_rif),
    ]], colWidths=[9 * cm, 7 * cm])
    footer_top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), azul),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (1, 0), (1, 0), 10),
    ]))
    story.append(footer_top)

    footer_dir = Table([[
        Paragraph(
            "📍 C.C Profesional Guacara Plaza, Nivel PB, Local PB-12. Guacara, Carabobo.  "
            "✉ info@rapicreditca.com  🌐 rapicreditca.com  📷 rapicreditca  📞 0412 314 66 89",
            s_footer_dir,
        )
    ]], colWidths=[16 * cm])
    footer_dir.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#2B5BAA")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(footer_dir)

    doc.build(story)
    return buf.getvalue()


def generar_carta_cobranza_pdf(contexto_cobranza: dict, db=None, logo_path: Optional[str] = None) -> bytes:
    """
    Genera el PDF de la carta de cobranza a partir del contexto (mismo que el email).
    contexto_cobranza: dict con CLIENTES.*, PRESTAMOS.ID, FECHA_CARTA, CUOTAS.VENCIMIENTOS, etc.
    Todas las variables {{KEY}} y {KEY} en la plantilla se sustituyen por datos reales de BD.
    db: sesión opcional para cargar plantilla editable (config plantilla_pdf_cobranza).
    logo_path: ruta al logo PNG (opcional; si no se pasa se intenta desde settings).
    """
    plantilla = _get_plantilla_pdf_config(db)
    datos = _datos_desde_contexto(contexto_cobranza, plantilla)
    if not logo_path:
        try:
            from app.core.config import settings
            logo_path = getattr(settings, "LOGO_PDF_COBRANZA_PATH", None)
        except Exception:
            logo_path = None
    cuerpo = _reemplazar_variables_plantilla_pdf(
        plantilla.get("cuerpo_principal"), contexto_cobranza, datos
    )
    clausula = _reemplazar_variables_plantilla_pdf(
        plantilla.get("clausula_septima"), contexto_cobranza, datos
    )
    return build_pdf_bytes(datos, logo_path=logo_path, cuerpo_principal=cuerpo or None, clausula_septima=clausula or None)
