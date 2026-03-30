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



# Paleta documento (legible en impresion y pantalla)

COLOR_HEADER = "#0c2444"

COLOR_ACCENT = "#b8942e"

COLOR_HEADER_BG = "#0f2d52"

COLOR_ROW_ALT = "#f1f5f9"

COLOR_BORDER = "#cbd5e1"

COLOR_TEXT_MUTED = "#64748b"

COLOR_SURFACE = "#f8fafc"

def generar_pdf_estado_cuenta(
    cedula: str,
    nombre: str,
    prestamos: List[dict],
    cuotas_pendientes: List[dict],
    total_pendiente: float,
    fecha_corte: date,
    amortizaciones_por_prestamo: Optional[List[dict]] = None,
    pagos_realizados: Optional[List[dict]] = None,
    recibos: Optional[List[dict]] = None,
    recibo_token: Optional[str] = None,
    base_url: str = "",
) -> bytes:
    """PDF estado de cuenta: layout corporativo, tablas homogeneas, datos desde parametros."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def hc(hex_color: str):
        return colors.HexColor(hex_color)

    hdr_bg = hc(COLOR_HEADER_BG)
    border_m = hc(COLOR_BORDER)
    alt_bg = hc(COLOR_ROW_ALT)
    surf = hc(COLOR_SURFACE)
    accent = hc(COLOR_ACCENT)
    text_dark = hc("#1e293b")

    def tbl_style(nrows: int, *, nhead: int = 1, hf: int = 9, bf: int = 9, extras=None):
        extras = extras or []
        h_end = nhead - 1
        st = [
            ("BACKGROUND", (0, 0), (-1, h_end), hdr_bg),
            ("TEXTCOLOR", (0, 0), (-1, h_end), colors.white),
            ("FONTNAME", (0, 0), (-1, h_end), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, h_end), hf),
            ("LINEBELOW", (0, 0), (-1, h_end), 1.2, accent),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.55, border_m),
        ]
        if nrows > nhead:
            st.append(("ROWBACKGROUNDS", (0, nhead), (-1, -1), [colors.white, alt_bg]))
        st.extend(
            [
                ("FONTNAME", (0, nhead), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, nhead), (-1, -1), bf),
                ("TEXTCOLOR", (0, nhead), (-1, -1), text_dark),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, border_m),
            ]
        )
        st.extend(extras)
        return TableStyle(st)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.55 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        title="Estado de cuenta",
        author="RapiCredit",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="EC_Section",
            fontSize=11.5,
            textColor=hc(COLOR_HEADER),
            spaceBefore=14,
            spaceAfter=8,
            fontName="Helvetica-Bold",
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EC_Muted",
            fontSize=9,
            textColor=hc(COLOR_TEXT_MUTED),
            spaceAfter=4,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EC_Link",
            fontSize=8,
            textColor=accent,
            leading=10,
        )
    )

    story = []

    # ----- Cabecera -----
    titulo = Paragraph(
        f'<font name="Helvetica-Bold" size="20" color="{COLOR_HEADER}">Estado de cuenta</font>',
        ParagraphStyle(name="EC_Tit", alignment=1, spaceAfter=2),
    )
    subt = Paragraph(
        f'<font size="9" color="{COLOR_TEXT_MUTED}">Corte al {fecha_corte.strftime("%d/%m/%Y")} &mdash; documento informativo</font>',
        ParagraphStyle(name="EC_Sub", alignment=1, spaceAfter=8, leading=12),
    )
    if _LOGO_PATH.exists():
        logo = Image(str(_LOGO_PATH), width=1.45 * inch, height=1.45 * inch)
        head_tbl = Table([[logo, [titulo, subt]]], colWidths=[1.85 * inch, 5.5 * inch], rowHeights=[1.5 * inch])
        head_tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (1, 0), (1, 0), 12),
                ]
            )
        )
        story.append(head_tbl)
    else:
        story.append(titulo)
        story.append(subt)
    story.append(Spacer(1, 8))
    bar = Table([[""]], colWidths=[7.35 * inch], rowHeights=[2.5])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), accent)]))
    story.append(bar)
    story.append(Spacer(1, 16))

    # ----- Cliente -----
    cli_left = Paragraph(
        f'<font size="8" color="{COLOR_TEXT_MUTED}">Cliente</font><br/>'
        f'<font size="11" color="{COLOR_HEADER}"><b>{nombre or "-"}</b></font>',
        ParagraphStyle(name="EC_CliL", leading=14),
    )
    cli_right = Paragraph(
        f'<font size="8" color="{COLOR_TEXT_MUTED}">Cédula</font><br/>'
        f'<font size="11" color="{COLOR_HEADER}"><b>{cedula}</b></font>',
        ParagraphStyle(name="EC_CliR", leading=14),
    )
    cli_tbl = Table([[cli_left, cli_right]], colWidths=[3.65 * inch, 3.7 * inch])
    cli_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), surf),
                ("BOX", (0, 0), (-1, -1), 0.5, border_m),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(cli_tbl)
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
"Los pagos de la sección <b>Pagos realizados</b> (Subtotal en USD) se aplican a las cuotas en orden por número de cuota; en la amortización, la columna <b>Pago</b> muestra cuánto de esos pagos quedó aplicado a cada cuota en USD.",
            styles["EC_Muted"],
        )
    )
    story.append(Spacer(1, 6))

    # ----- Préstamos -----
    if prestamos:
        story.append(Paragraph("Préstamos", styles["EC_Section"]))
        rows = [["Id", "Producto", "Total financiamiento", "Estado"]]
        for p in prestamos:
            rows.append(
                [
                    str(p.get("id", "")),
                    (p.get("producto") or "-")[:42],
                    f"{float(p.get('total_financiamiento') or 0):,.2f}",
                    (p.get("estado") or "-")[:22],
                ]
            )
        t = Table(rows, colWidths=[42, 188, 92, 82])
        t.setStyle(
            tbl_style(
                len(rows),
                hf=9,
                bf=9,
                extras=[
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ],
            )
        )
        story.append(t)
        story.append(Spacer(1, 10))

    # ----- Pagos realizados (tabla pagos) -----
    pagos_realizados = pagos_realizados or []
    if pagos_realizados:
        # Ordenar por fecha de pago descendente (más actual a más vieja)
        from datetime import datetime as dt_parse
        def parse_fecha(fecha_str):
            try:
                if fecha_str and len(fecha_str) >= 10:
                    return dt_parse.strptime(fecha_str[:10], "%Y-%m-%d")
            except (ValueError, AttributeError):
                pass
            return dt_parse.min
        pagos_realizados = sorted(
            pagos_realizados,
            key=lambda x: parse_fecha(x.get("fecha_pago") or ""),
            reverse=True
        )
        story.append(Paragraph("Pagos realizados", styles["EC_Section"]))
        rows_p = [
            [
                "Fecha de pago",
                "Fecha ingreso sistema",
                "Monto",
                "Tasa",
                "Subtotal (USD)",
                "Recibo",
            ]
        ]
        total_usd = 0.0
        for pr in pagos_realizados:
            total_usd += float(pr.get("subtotal_usd") or 0)
            pago_row_id = pr.get("pago_id")
            puede_rec = bool(pago_row_id and base_url and recibo_token)
            if puede_rec:
                url_r = f"{base_url}/api/v1/estado-cuenta/public/recibo-pago?token={recibo_token}&pago_id={pago_row_id}"
                rec_cell = Paragraph(
                    f'<a href="{url_r}" color="{COLOR_ACCENT}">Ver recibo</a>',
                    styles["EC_Link"],
                )
            else:
                rec_cell = Paragraph('<font color="#94a3b8">-</font>', styles["EC_Link"])
            rows_p.append(
                [
                    str(pr.get("fecha_pago_display") or "-")[:16],
                    str(pr.get("fecha_registro_display") or "-")[:16],
                    str(pr.get("monto_display") or "-")[:22],
                    str(pr.get("tasa_display") or "-")[:12],
                    f"{float(pr.get('subtotal_usd') or 0):,.2f}",
                    rec_cell,
                ]
            )
        rows_p.append(
            [
                Paragraph("<b>Total pagado (USD)</b>", styles["Normal"]),
                "",
                "",
                "",
                Paragraph(f"<b>{total_usd:,.2f}</b>", styles["Normal"]),
                "",
            ]
        )
        nrp = len(rows_p)
        tp = Table(
            rows_p,
            colWidths=[
                1.1 * inch,
                1.1 * inch,
                1.2 * inch,
                0.7 * inch,
                1.1 * inch,
                0.9 * inch,
            ],
        )
        extras_p = [
            ("ALIGN", (4, 0), (4, nrp - 2), "RIGHT"),
            ("ALIGN", (4, nrp - 1), (4, nrp - 1), "RIGHT"),
            ("SPAN", (0, nrp - 1), (3, nrp - 1)),
            ("ALIGN", (0, nrp - 1), (3, nrp - 1), "RIGHT"),
            ("FONTNAME", (0, nrp - 1), (-1, nrp - 1), "Helvetica-Bold"),
            ("BACKGROUND", (0, nrp - 1), (-1, nrp - 1), surf),
        ]
        tp.setStyle(tbl_style(nrp, hf=8, bf=7, extras=extras_p))
        story.append(tp)
        story.append(Spacer(1, 10))

    # ----- Cuotas pendientes -----
    story.append(Paragraph("Cuotas pendientes", styles["EC_Section"]))
    story.append(
        Paragraph(
            f'Total pendiente: <b><font color="{COLOR_HEADER}">{float(total_pendiente or 0):,.2f} USD</font></b>',
            ParagraphStyle(name="EC_TotPen", fontSize=10, spaceAfter=8),
        )
    )
    if not cuotas_pendientes:
        story.append(Paragraph("No hay cuotas pendientes.", styles["EC_Muted"]))
    else:
        rows = [["Préstamo", "Nº cuota", "Vencimiento", "Monto", "Estado"]]
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
                    (c.get("estado_etiqueta") or etiqueta_estado_cuota(str(c.get("estado") or "")))[:34],
                ]
            )
        t = Table(rows, colWidths=[58, 52, 78, 72, 86])
        t.setStyle(
            tbl_style(
                len(rows),
                extras=[
                    ("ALIGN", (0, 1), (1, -1), "CENTER"),
                    ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ],
            )
        )
        story.append(t)

    # ----- Amortización -----
    if amortizaciones_por_prestamo:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Tablas de amortización", styles["EC_Section"]))
        for item in amortizaciones_por_prestamo:
            prestamo_id = item.get("prestamo_id", "")
            producto = (item.get("producto") or "Préstamo")[:52]
            cuotas = item.get("cuotas") or []
            if not cuotas:
                continue
            story.append(Spacer(1, 4))
            story.append(
                Paragraph(
                    f'<font color="{COLOR_HEADER}"><b>Préstamo #{prestamo_id}</b></font> &nbsp; '
                    f'<font color="{COLOR_TEXT_MUTED}">{producto}</font>',
                    ParagraphStyle(name="EC_SubPrest", fontSize=10, spaceAfter=6, fontName="Helvetica"),
                )
            )
            rows = [
                [
                    "Cuota",
                    "F. venc.",
                    "Capital",
                    "Interés",
                    "Total",
                    "Saldo",
                    "Pago",
                    "Estado",
                ]
            ]
            for c in cuotas:
                estado_etiqueta = (c.get("estado_etiqueta") or "").strip() or etiqueta_estado_cuota(
                    c.get("estado") or ""
                )
                cuota_id = c.get("id")
                raw_tp = c.get("total_pagado_cuota")
                try:
                    total_aplicado = float(raw_tp) if raw_tp is not None else 0.0
                except (TypeError, ValueError):
                    total_aplicado = 0.0
                if total_aplicado <= 0:
                    disp = c.get("pago_conciliado_display")
                    if disp not in (None, "", "-"):
                        try:
                            total_aplicado = float(str(disp).replace(",", ""))
                        except ValueError:
                            total_aplicado = 0.0
                rows.append(
                    [
                        str(c.get("numero_cuota", "")),
                        (c.get("fecha_vencimiento") or ""),
                        f"{float(c.get('monto_capital') or 0):,.2f}",
                        f"{float(c.get('monto_interes') or 0):,.2f}",
                        f"{float(c.get('monto_cuota') or 0):,.2f}",
                        f"{float(c.get('saldo_capital_final') or 0):,.2f}",
                        c.get("pago_conciliado_display", "-"),
                        estado_etiqueta[:20],
                    ]
                )
            t = Table(
                rows,
                colWidths=[
                    0.40 * inch,
                    0.66 * inch,
                    0.94 * inch,
                    0.94 * inch,
                    1.00 * inch,
                    0.82 * inch,
                    0.76 * inch,
                    1.00 * inch,
                ],
            )
            t.setStyle(
                tbl_style(
                    len(rows),
                    hf=8,
                    bf=7,
                    extras=[
                        # Encabezado: Capital, Interes, Total centrados (referencia visual).
                        ("ALIGN", (2, 0), (4, 0), "CENTER"),
                        ("ALIGN", (0, 0), (1, 0), "CENTER"),
                        ("ALIGN", (5, 0), (7, 0), "CENTER"),
                        ("ALIGN", (0, 1), (0, -1), "CENTER"),
                        ("ALIGN", (2, 1), (6, -1), "RIGHT"),
                        ("ALIGN", (7, 1), (7, -1), "CENTER"),
                    ],
                )
            )
            story.append(t)
            story.append(Spacer(1, 8))

    # ----- Recibos cobranza -----
    recibos = recibos or []
    if recibos and base_url:
        story.append(Paragraph("Pagos reportados (recibos)", styles["EC_Section"]))
        rows = [["Referencia", "Fecha", "Monto", "Recibo"]]
        for r in recibos:
            ref = (r.get("referencia_interna") or "")[:22]
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
                link_cell = Paragraph(
                    f'<a href="{url}" color="{COLOR_ACCENT}">Ver recibo</a>',
                    styles["EC_Link"],
                )
            else:
                link_cell = Paragraph('<font color="#94a3b8">—</font>', styles["EC_Link"])
            rows.append([ref, fecha, monto, link_cell])
        t = Table(rows, colWidths=[108, 72, 88, 78])
        t.setStyle(
            tbl_style(
                len(rows),
                extras=[
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ],
            )
        )
        story.append(t)

    # ----- Pie -----
    story.append(Spacer(1, 22))
    foot_line = Table([[""]], colWidths=[7.35 * inch], rowHeights=[0.5])
    foot_line.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.5, border_m)]))
    story.append(foot_line)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f'<font size="8" color="{COLOR_TEXT_MUTED}">RapiCredit C.A. &middot; '
            f'cobranza@rapicreditca.com &middot; WhatsApp 424-4579934</font>',
            ParagraphStyle(name="EC_Foot", alignment=1, fontSize=8, textColor=hc(COLOR_TEXT_MUTED)),
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
    "COLOR_SURFACE",
    "COLOR_TEXT_MUTED",
    "ESTADOS_PRESTAMO_TABLA_AMORTIZACION",
    "generar_pdf_estado_cuenta",
    "obtener_datos_estado_cuenta_cliente",
    "obtener_datos_estado_cuenta_prestamo",
    "obtener_recibos_cliente_estado_cuenta",
    "prestamo_muestra_tabla_amortizacion",
    "serializar_estado_cuenta_payload_json",
]

