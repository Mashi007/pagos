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

    def tbl_style(nrows: int, *, nhead: int = 1, hf: int = 9, bf: int = 9, extras=None, no_rowbg: bool = False):
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
        if nrows > nhead and not no_rowbg:
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
    _pfx = str(id(buf))  # unique per call; avoids ReportLab style registry collisions
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
        ParagraphStyle(name="EC_Tit", alignment=1, spaceAfter=12, leading=24),
    )
    subt = Paragraph(
        f'<font size="9" color="{COLOR_TEXT_MUTED}">Corte al {fecha_corte.strftime("%d/%m/%Y")} &mdash; documento informativo</font>',
        ParagraphStyle(name="EC_Sub", alignment=1, spaceAfter=8, leading=12),
    )
    if _LOGO_PATH.exists():
        logo = Image(str(_LOGO_PATH), width=1.45 * inch, height=1.45 * inch)
        head_tbl = Table([[logo, [titulo, subt]]], colWidths=[1.85 * inch, 5.5 * inch], rowHeights=[1.8 * inch])
        head_tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
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
"Los pagos de la sección <b>Pagos realizados</b> (Subtotal en USD) se aplican a las cuotas en orden por número de cuota.",
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
                "F. ingreso",
                "Monto",
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
                    f"{float(pr.get('subtotal_usd') or 0):,.2f}",
                    rec_cell,
                ]
            )
        rows_p.append(
            [
                Paragraph("<b>Total pagado (USD)</b>", styles["Normal"]),
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
                1.20 * inch,
                1.10 * inch,
                1.25 * inch,
                1.20 * inch,
                0.80 * inch,
            ],
        )
        extras_p = [
            ("ALIGN", (3, 0), (3, nrp - 2), "RIGHT"),
            ("ALIGN", (3, nrp - 1), (3, nrp - 1), "RIGHT"),
            ("SPAN", (0, nrp - 1), (2, nrp - 1)),
            ("ALIGN", (0, nrp - 1), (2, nrp - 1), "RIGHT"),
            ("FONTNAME", (0, nrp - 1), (-1, nrp - 1), "Helvetica-Bold"),
            ("BACKGROUND", (0, nrp - 1), (-1, nrp - 1), surf),
        ]
        tp.setStyle(tbl_style(nrp, hf=8, bf=7, extras=extras_p))
        story.append(tp)
        story.append(Spacer(1, 10))

    # Indice: numero_cuota -> lista de pagos que la cubrieron (para cruzar con Plan de pago)
    _cuota_pagos_idx: dict = {}  # {numero_cuota: [{"fecha": str, "ref": str, "monto": float}]}
    for _pr in (pagos_realizados or []):
        _fecha_pr = (str(_pr.get("fecha_pago_display") or ""))[:10]
        _ref_pr   = (str(_pr.get("referencia_tabla") or _pr.get("numero_documento") or "") or f"Pago #{_pr.get('pago_id','')}").strip()[:20]
        for _apl in (_pr.get("aplicacion_cuotas") or []):
            _nc  = int(_apl.get("numero_cuota") or 0)
            _apl_m = float(_apl.get("monto_aplicado") or 0)
            if _nc and _apl_m > 0:
                _cuota_pagos_idx.setdefault(_nc, []).append({
                    "fecha": _fecha_pr,
                    "ref":   _ref_pr,
                    "monto": _apl_m,
                })

    # ----- Plan de pago (didactico con barra de progreso) -----
    if amortizaciones_por_prestamo:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Plan de pago", styles["EC_Section"]))
        for item in amortizaciones_por_prestamo:
            prestamo_id = item.get("prestamo_id", "")
            producto = (item.get("producto") or "Pr\ufffd stamo")[:52]
            cuotas = item.get("cuotas") or []
            if not cuotas:
                continue

            # --- Calcular totales para barra de progreso ---
            n_total = len(cuotas)
            n_pagadas = sum(
                1 for c in cuotas
                if (c.get("estado") or "").strip().upper() in ("PAGADO", "PAGADA", "PAGO_ADELANTADO")
            )
            pct = n_pagadas / n_total if n_total else 0

            story.append(Spacer(1, 4))
            story.append(
                Paragraph(
                    f'<font color="{COLOR_HEADER}"><b>Pr\ufffd stamo #{prestamo_id}</b></font>'
                    f' &nbsp; <font color="{COLOR_TEXT_MUTED}" size="9">{producto}</font>',
                    ParagraphStyle(name=f"EC_SP_{_pfx}_{prestamo_id}", fontSize=10, spaceAfter=4, fontName="Helvetica"),
                )
            )

            # --- Barra de progreso ---
            BAR_W = 7.35 * inch
            filled_pct = max(0.05, pct)  # minimo 5% para visibilidad
            filled = filled_pct * BAR_W
            empty = max(0.01, BAR_W - filled)
            bar_label = f"{n_pagadas}/{n_total} cuotas pagadas  ({pct*100:.0f}%)"
            _bt_style = ParagraphStyle(name=f"EC_BT_{_pfx}_{prestamo_id}", alignment=1, leading=10)
            # Fila 0: etiqueta centrada sobre toda la barra (SPAN)
            # Fila 1: segmento azul (pagado) + segmento gris (pendiente)
            bar_cells = [
                [Paragraph(f'<font color="{COLOR_HEADER}" size="8"><b>{bar_label}</b></font>', _bt_style), ""],
                ["", ""],
            ]
            bar_tbl = Table(bar_cells, colWidths=[filled, empty], rowHeights=[13, 8])
            bar_tbl.setStyle(TableStyle([
                # Fila 0: fondo blanco, texto centrado que ocupa las 2 columnas
                ("SPAN",       (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (1, 0), colors.white),
                ("ALIGN",      (0, 0), (1, 0), "CENTER"),
                ("VALIGN",     (0, 0), (1, 0), "MIDDLE"),
                # Fila 1: barra bicolor
                ("BACKGROUND", (0, 1), (0, 1), hc(COLOR_HEADER)),
                ("BACKGROUND", (1, 1), (1, 1), hc(COLOR_BORDER)),
                # Padding
                ("LEFTPADDING",   (0, 0), (-1, -1), 2),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN",        (0, 1), (1, 1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, hc(COLOR_BORDER)),
            ]))
            story.append(bar_tbl)
            story.append(Spacer(1, 2))

            # --- Leyenda colores ---
            leyenda_style = ParagraphStyle(name=f"EC_LY_{_pfx}_{prestamo_id}", fontSize=7, leading=9, textColor=hc(COLOR_TEXT_MUTED))
            leyenda = Paragraph(
                f'<font color="{COLOR_HEADER}">&#9632;</font> Pagada &nbsp;&nbsp;'
                f'<font color="{COLOR_ACCENT}">&#9632;</font> Parcial &nbsp;&nbsp;'
                f'<font color="{COLOR_BORDER}">&#9632;</font> Pendiente',
                leyenda_style,
            )
            story.append(leyenda)
            story.append(Spacer(1, 4))

            # --- Tabla ---
            rows = [["#", "Vence", "Cuota (USD)", "Pagado (USD)", "Saldo (USD)", "Estado"]]
            for c in cuotas:
                estado_codigo = (c.get("estado") or "").strip().upper()
                estado_etiqueta = (c.get("estado_etiqueta") or "").strip() or etiqueta_estado_cuota(estado_codigo)
                monto_cuota = float(c.get("monto_cuota") or 0)
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

                es_pagada = estado_codigo in ("PAGADO", "PAGADA", "PAGO_ADELANTADO")
                es_parcial = (not es_pagada) and total_aplicado > 0

                _nc_key = int(c.get('numero_cuota') or 0)
                _orig_pagos = _cuota_pagos_idx.get(_nc_key, [])
                # Lineas de origen: fecha + referencia del pago que cubrió esta cuota
                _orig_lines = ''
                for _op in _orig_pagos:
                    _op_txt = f"{_op['fecha']}  {_op['ref']}  ({_op['monto']:,.2f})"
                    _orig_lines += f'<br/><font size="6" color="{COLOR_TEXT_MUTED}">{_op_txt}</font>'

                cell_link = ParagraphStyle(name=f"EC_CL_{_pfx}_{prestamo_id}_{c.get('numero_cuota','x')}", fontSize=8, leading=10)
                if es_pagada:
                    pagado_txt = f'<font color="{COLOR_HEADER}"><b>{total_aplicado:,.2f}</b></font>{_orig_lines}'
                    estado_txt = f'<font color="{COLOR_HEADER}"><b>{estado_etiqueta[:18]}</b></font>'
                elif es_parcial:
                    pagado_txt = f'<font color="{COLOR_ACCENT}"><b>{total_aplicado:,.2f}</b></font> <font size="7" color="{COLOR_ACCENT}">(parcial)</font>{_orig_lines}'
                    estado_txt = f'<font color="{COLOR_ACCENT}">{estado_etiqueta[:18]}</font>'
                else:
                    pagado_txt = f'<font color="{COLOR_TEXT_MUTED}">-</font>'
                    estado_txt = f'<font color="{COLOR_TEXT_MUTED}">{estado_etiqueta[:18]}</font>'

                rows.append([
                    str(c.get("numero_cuota", "")),
                    (c.get("fecha_vencimiento") or ""),
                    f"{monto_cuota:,.2f}",
                    Paragraph(pagado_txt, cell_link),
                    f"{float(c.get('saldo_capital_final') or 0):,.2f}",
                    Paragraph(estado_txt, cell_link),
                ])

            # Colores por fila segun estado
            tbl_extras = [
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (2, 1), (4, -1), "RIGHT"),
                ("ALIGN", (5, 0), (5, -1), "CENTER"),
            ]
            for idx, c in enumerate(cuotas, 1):
                ec = (c.get("estado") or "").strip().upper()
                raw_tp2 = c.get("total_pagado_cuota")
                try:
                    tap2 = float(raw_tp2) if raw_tp2 is not None else 0.0
                except (TypeError, ValueError):
                    tap2 = 0.0
                if ec in ("PAGADO", "PAGADA", "PAGO_ADELANTADO"):
                    tbl_extras.append(("BACKGROUND", (0, idx), (-1, idx), hc("#e8f0fe")))
                elif tap2 > 0:
                    tbl_extras.append(("BACKGROUND", (0, idx), (-1, idx), hc("#fef9ec")))

            t_amort = Table(
                rows,
                colWidths=[
                    0.38 * inch,
                    0.80 * inch,
                    1.00 * inch,
                    1.20 * inch,
                    1.00 * inch,
                    1.20 * inch,
                ],
            )
            t_amort.setStyle(tbl_style(len(rows), hf=8, bf=8, extras=tbl_extras, no_rowbg=True))
            story.append(t_amort)
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

