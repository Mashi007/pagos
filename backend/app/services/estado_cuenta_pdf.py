"""
PDF de estado de cuenta (ReportLab).

Datos canonicos: app.services.estado_cuenta_datos (ver backend/docs/ESTADO_CUENTA_FUENTE_UNICA.md).
"""

import io
import logging

from datetime import date

from pathlib import Path

from typing import List, Optional

from app.services.cuota_estado import etiqueta_estado_cuota

logger = logging.getLogger(__name__)


# Ruta al logo: backend/static/logo.png (desde app/services/ subimos a backend)

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "logo.png"



# Colores RapiCredit (azul corporativo, naranja acento)

COLOR_HEADER = "#1e3a5f"

COLOR_ACCENT = "#c4a35a"

COLOR_HEADER_BG = "#1e3a5f"

COLOR_ROW_ALT = "#f8fafc"

COLOR_BORDER = "#e2e8f0"

COLOR_TEXT_MUTED = "#64748b"





def generar_pdf_estado_cuenta(

    cedula: str,

    nombre: str,

    prestamos: List[dict],

    cuotas_pendientes: List[dict],

    total_pendiente: float,

    fecha_corte: date,

    amortizaciones_por_prestamo: Optional[List[dict]] = None,

    recibos: Optional[List[dict]] = None,

    recibo_token: Optional[str] = None,

    base_url: str = "",

) -> bytes:

    """

    Genera PDF de estado de cuenta con diseño profesional:

    logo, cabecera con marca, datos del cliente, tablas de préstamos, cuotas pendientes y amortización.

    """

    from reportlab.lib import colors

    from reportlab.lib.pagesizes import letter

    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    from reportlab.lib.units import inch

    from reportlab.platypus import (

        SimpleDocTemplate,

        Table,

        TableStyle,

        Paragraph,

        Spacer,

        Image,

    )



    buf = io.BytesIO()

    doc = SimpleDocTemplate(

        buf,

        pagesize=letter,

        topMargin=0.6 * inch,

        bottomMargin=0.6 * inch,

        leftMargin=0.6 * inch,

        rightMargin=0.6 * inch,

    )

    styles = getSampleStyleSheet()



    # Estilos personalizados RapiCredit

    styles.add(

        ParagraphStyle(

            name="DocTitle",

            fontSize=18,

            textColor=COLOR_HEADER,

            spaceAfter=4,

            fontName="Helvetica-Bold",

            alignment=1,

        )

    )

    styles.add(

        ParagraphStyle(

            name="SectionTitle",

            fontSize=12,

            textColor=COLOR_HEADER,

            spaceBefore=14,

            spaceAfter=6,

            fontName="Helvetica-Bold",

        )

    )

    styles.add(

        ParagraphStyle(

            name="InfoText",

            fontSize=10,

            textColor=COLOR_TEXT_MUTED,

            spaceAfter=2,

        )

    )

    styles.add(

        ParagraphStyle(

            name="TotalLabel",

            fontSize=11,

            fontName="Helvetica-Bold",

            textColor=COLOR_HEADER,

            spaceAfter=4,

        )

    )



    story = []



    # ----- Cabecera: logo + título -----

    if _LOGO_PATH.exists():

        logo_img = Image(str(_LOGO_PATH), width=1.8 * inch, height=1.8 * inch)

        story.append(logo_img)

        story.append(Spacer(1, 6))

    story.append(Paragraph("Estado de cuenta", styles["DocTitle"]))

    story.append(

        Paragraph(

            f'<font color="{COLOR_TEXT_MUTED}" size="9">Fecha de corte: {fecha_corte.strftime("%d/%m/%Y")}</font>',

            styles["Normal"],

        )

    )

    story.append(Spacer(1, 14))



    # ----- Datos del cliente -----

    story.append(

        Paragraph(

            f'<b>Cédula:</b> {cedula} &nbsp;&nbsp;&nbsp; <b>Cliente:</b> {nombre or "-"}',

            styles["InfoText"],

        )

    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "Asignación en cascada: los pagos conciliados se aplican a las cuotas "
            "en orden por número de cuota.",
            styles["InfoText"],
        )
    )
    story.append(Spacer(1, 8))

    # ----- Tabla Préstamos -----

    if prestamos:

        story.append(Paragraph("Préstamos", styles["SectionTitle"]))

        rows = [["Id", "Producto", "Total financiamiento", "Estado"]]

        for p in prestamos:

            rows.append(

                [

                    str(p.get("id", "")),

                    (p.get("producto") or "-")[:40],

                    f"{float(p.get('total_financiamiento') or 0):,.2f}",

                    (p.get("estado") or "-")[:20],

                ]

            )

        t = Table(rows, colWidths=[40, 180, 90, 80])

        t.setStyle(

            TableStyle(

                [

                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),

                    ("TEXTCOLOR", (0, 0), (-1, 0), "white"),

                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                    ("FONTSIZE", (0, 0), (-1, 0), 9),

                    ("ALIGN", (0, 0), (0, -1), "CENTER"),

                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),

                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),

                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", COLOR_ROW_ALT]),

                    ("FONTSIZE", (0, 1), (-1, -1), 9),

                ]

            )

        )

        story.append(t)

        story.append(Spacer(1, 12))



    # ----- Cuotas pendientes -----

    story.append(Paragraph("Cuotas pendientes", styles["SectionTitle"]))

    story.append(

        Paragraph(

            f'Total pendiente: <b><font color="{COLOR_HEADER}">{float(total_pendiente or 0):,.2f}</font></b>',

            styles["Normal"],

        )

    )

    if not cuotas_pendientes:

        story.append(

            Paragraph(

                '<font color="{}">No hay cuotas pendientes.</font>'.format(COLOR_TEXT_MUTED),

                styles["Normal"],

            )

        )

    else:

        rows = [["Préstamo", "Nº Cuota", "Vencimiento", "Monto", "Estado"]]

        for c in cuotas_pendientes:

            fv = c.get("fecha_vencimiento", "")

            if len(fv) >= 10 and fv[4] == "-":

                try:

                    from datetime import datetime as _dt

                    fv = _dt.strptime(fv[:10], "%Y-%m-%d").strftime("%d/%m/%Y")

                except Exception:

                    pass

            rows.append(

                [

                    str(c.get("prestamo_id", "")),

                    str(c.get("numero_cuota", "")),

                    fv,

                    f"{float(c.get('monto') or 0):,.2f}",

                    (c.get("estado_etiqueta") or etiqueta_estado_cuota(str(c.get("estado") or "")))[:32],

                ]

            )

        t = Table(rows, colWidths=[60, 55, 75, 70, 80])

        t.setStyle(

            TableStyle(

                [

                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),

                    ("TEXTCOLOR", (0, 0), (-1, 0), "white"),

                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                    ("FONTSIZE", (0, 0), (-1, 0), 9),

                    ("ALIGN", (0, 0), (1, -1), "CENTER"),

                    ("ALIGN", (3, 0), (3, -1), "RIGHT"),

                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),

                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", COLOR_ROW_ALT]),

                    ("FONTSIZE", (0, 1), (-1, -1), 9),

                ]

            )

        )

        story.append(t)



    # ----- Tablas de amortización -----

    if amortizaciones_por_prestamo:

        story.append(Spacer(1, 16))

        story.append(Paragraph("Tablas de amortización", styles["SectionTitle"]))

        for item in amortizaciones_por_prestamo:

            prestamo_id = item.get("prestamo_id", "")

            producto = (item.get("producto") or "Préstamo")[:50]

            cuotas = item.get("cuotas") or []

            if not cuotas:

                continue

            story.append(Spacer(1, 8))

            story.append(

                Paragraph(

                    f'Préstamo #{prestamo_id} — {producto}',

                    ParagraphStyle(

                        name="SubSection",

                        fontSize=10,

                        textColor=COLOR_HEADER,

                        fontName="Helvetica-Bold",

                        spaceAfter=6,

                    ),

                )

            )

            style_recibo_link = ParagraphStyle(

                name="ReciboCuotaLink",

                fontSize=8,

                textColor=COLOR_HEADER,

                spaceAfter=2,

            )

            rows = [

                [

                    "Cuota",

                    "F. Venc.",

                    "Capital",

                    "Interés",

                    "Total",

                    "Saldo",

                    "Pago conc.",

                    "Estado",

                    "Recibo",

                ]

            ]

            for c in cuotas:

                estado_codigo = (c.get("estado") or "").strip().upper()

                estado_etiqueta = (c.get("estado_etiqueta") or "").strip() or etiqueta_estado_cuota(c.get("estado") or "")

                cuota_id = c.get("id")

                # PAGADA: mismo codigo que en cuota_estado / UI (etiqueta Pagado).
                puede_recibo = (

                    estado_codigo in ("PAGADO", "PAGADA", "PAGO_ADELANTADO")

                    and cuota_id

                    and base_url

                    and recibo_token

                )

                if puede_recibo:

                    url_recibo = f"{base_url}/api/v1/estado-cuenta/public/recibo-cuota?token={recibo_token}&prestamo_id={prestamo_id}&cuota_id={cuota_id}"

                    recibo_cell = Paragraph(f'<a href="{url_recibo}" color="{COLOR_HEADER}">Ver recibo</a>', style_recibo_link)

                else:

                    recibo_cell = Paragraph("&mdash;", style_recibo_link)

                rows.append(

                    [

                        str(c.get("numero_cuota", "")),

                        (c.get("fecha_vencimiento") or ""),

                        f"{float(c.get('monto_capital') or 0):,.2f}",

                        f"{float(c.get('monto_interes') or 0):,.2f}",

                        f"{float(c.get('monto_cuota') or 0):,.2f}",

                        f"{float(c.get('saldo_capital_final') or 0):,.2f}",

                        c.get("pago_conciliado_display", "-"),

                        estado_etiqueta[:22],

                        recibo_cell,

                    ]

                )

            t = Table(

                rows,

                colWidths=[32, 46, 44, 40, 46, 44, 44, 58, 50],

            )

            t.setStyle(

                TableStyle(

                    [

                        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),

                        ("TEXTCOLOR", (0, 0), (-1, 0), "white"),

                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                        ("FONTSIZE", (0, 0), (-1, 0), 8),

                        ("ALIGN", (0, 0), (0, -1), "CENTER"),

                        ("ALIGN", (2, 0), (6, -1), "RIGHT"),

                        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),

                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", COLOR_ROW_ALT]),

                        ("FONTSIZE", (0, 1), (-1, -1), 8),

                    ]

                )

            )

            story.append(t)

            story.append(Spacer(1, 12))



    # ----- Pagos realizados (recibos) -----

    recibos = recibos or []

    if recibos and base_url:

        story.append(Spacer(1, 16))

        story.append(Paragraph("Pagos realizados (recibos)", styles["SectionTitle"]))

        style_link = ParagraphStyle(

            name="ReciboLink",

            fontSize=9,

            textColor=COLOR_HEADER,

            spaceAfter=2,

        )

        rows = [["Referencia", "Fecha", "Monto", "Recibo"]]

        for r in recibos:

            ref = (r.get("referencia_interna") or "")[:20]

            fecha = (r.get("fecha_pago") or "")[:10]

            if len(fecha) >= 10 and fecha[4] == "-":

                try:

                    from datetime import datetime as _dt

                    fecha = _dt.strptime(fecha[:10], "%Y-%m-%d").strftime("%d/%m/%Y")

                except Exception:

                    pass

            monto = f"{float(r.get('monto') or 0):,.2f} {r.get('moneda') or 'BS'}"

            pago_id = r.get("id", "")

            if base_url and pago_id:

                if recibo_token:

                    url = f"{base_url}/api/v1/cobros/public/recibo?token={recibo_token}&pago_id={pago_id}"

                else:

                    url = f"{base_url}/api/v1/cobros/pagos-reportados/{pago_id}/recibo.pdf"

                link_cell = Paragraph(f'<a href="{url}" color="{COLOR_HEADER}">Ver recibo</a>', style_link)

            else:

                link_cell = Paragraph("&mdash;", style_link)

            rows.append([ref, fecha, monto, link_cell])

        t = Table(rows, colWidths=[100, 70, 85, 75])

        t.setStyle(

            TableStyle([

                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),

                ("TEXTCOLOR", (0, 0), (-1, 0), "white"),

                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                ("FONTSIZE", (0, 0), (-1, 0), 9),

                ("ALIGN", (0, 0), (1, -1), "LEFT"),

                ("ALIGN", (2, 0), (2, -1), "RIGHT"),

                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),

                ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", COLOR_ROW_ALT]),

                ("FONTSIZE", (0, 1), (-1, -1), 9),

            ])

        )

        story.append(t)

        story.append(Spacer(1, 12))



    # ----- Pie -----

    story.append(Spacer(1, 20))

    story.append(

        Paragraph(

            f'<font color="{COLOR_TEXT_MUTED}" size="8">Documento generado por RapiCredit C.A. — cobranza@rapicreditca.com — WhatsApp 424-4579934</font>',

            ParagraphStyle(name="Footer", alignment=1, spaceBefore=8),

        )

    )



    doc.build(story)

    return buf.getvalue()

# Re-export: datos canonicos viven en estado_cuenta_datos (compatibilidad imports historicos).
from app.services.estado_cuenta_datos import (  # noqa: E402
    ESTADOS_PRESTAMO_TABLA_AMORTIZACION,
    obtener_datos_estado_cuenta_cliente,
    obtener_datos_estado_cuenta_prestamo,
    obtener_recibos_cliente_estado_cuenta,
    prestamo_muestra_tabla_amortizacion,
    serializar_estado_cuenta_payload_json,
)

__all__ = [
    "COLOR_ACCENT",
    "COLOR_BORDER",
    "COLOR_HEADER",
    "COLOR_HEADER_BG",
    "COLOR_ROW_ALT",
    "COLOR_TEXT_MUTED",
    "ESTADOS_PRESTAMO_TABLA_AMORTIZACION",
    "generar_pdf_estado_cuenta",
    "obtener_datos_estado_cuenta_cliente",
    "obtener_datos_estado_cuenta_prestamo",
    "obtener_recibos_cliente_estado_cuenta",
    "prestamo_muestra_tabla_amortizacion",
    "serializar_estado_cuenta_payload_json",
]

