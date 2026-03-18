# Patch estado_cuenta_pdf: add recibos section with links
path = "app/services/estado_cuenta_pdf.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add parameters to function signature
old_sig = """def generar_pdf_estado_cuenta(
    cedula: str,
    nombre: str,
    prestamos: List[dict],
    cuotas_pendientes: List[dict],
    total_pendiente: float,
    fecha_corte: date,
    amortizaciones_por_prestamo: Optional[List[dict]] = None,
) -> bytes:"""

new_sig = """def generar_pdf_estado_cuenta(
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
) -> bytes:"""

content = content.replace(old_sig, new_sig)

# 2) Insert "Pagos realizados" section before "# ----- Pie -----"
old_pie = """    # ----- Pie -----
    story.append(Spacer(1, 20))"""

new_pie = '''    # ----- Pagos realizados (recibos) -----
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
            if recibo_token:
                url = f"{base_url}/api/v1/cobros/public/recibo?token={recibo_token}&pago_id={r.get('id', '')}"
            else:
                url = f"{base_url}/api/v1/cobros/pagos-reportados/{r.get('id', '')}/recibo.pdf"
            link_cell = Paragraph(f'<a href="{url}" color="{COLOR_HEADER}">Ver recibo</a>', style_link)
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
    story.append(Spacer(1, 20))'''

content = content.replace(old_pie, new_pie)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("estado_cuenta_pdf.py patched.")
