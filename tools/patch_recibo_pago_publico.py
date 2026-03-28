# Patch estado_cuenta_publico.py and estado_cuenta_pdf.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ep = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
t = ep.read_text(encoding="utf-8")

imp_old = "from app.services.estado_cuenta_datos import obtener_recibos_cliente_estado_cuenta\n"
imp_new = (
    "from app.services.estado_cuenta_datos import (\n"
    "    desglose_aplicacion_cuotas_por_pago,\n"
    "    obtener_recibos_cliente_estado_cuenta,\n"
    ")\n"
    "from app.services.cobros.recibo_pdf import _formato_monto_venezolano\n"
    "from app.services.cobros.recibo_pago_cartera_pdf import generar_recibo_pago_cartera_pdf\n"
)
if imp_old not in t:
    raise SystemExit("import block not found estado_cuenta_publico")
t = t.replace(imp_old, imp_new, 1)

route = '''


@router.get("/recibo-pago")
def get_recibo_pago_cartera_publico(
    token: str = Query(..., description="Token de sesion estado de cuenta"),
    pago_id: int = Query(..., description="ID del pago en tabla pagos (cartera)"),
    db: Session = Depends(get_db),
):
    """
    PDF del recibo anclado al pago PAGADO de cartera (tabla pagos).
    Token: misma cedula que el titular del prestamo del pago.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "recibo":
        raise HTTPException(status_code=401, detail="Token invalido o expirado.")
    cedula_token = (payload.get("sub") or "").strip().replace("-", "").replace(" ", "")
    if not cedula_token:
        raise HTTPException(status_code=401, detail="Token invalido.")
    pago = db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    if (getattr(pago, "estado", None) or "").strip().upper() != "PAGADO":
        raise HTTPException(status_code=400, detail="El pago no esta en estado PAGADO.")
    prestamo_id = getattr(pago, "prestamo_id", None)
    if not prestamo_id:
        raise HTTPException(status_code=400, detail="Pago sin prestamo asociado.")
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Prestamo no encontrado.")
    ced_prest = (getattr(prestamo, "cedula", None) or "").strip().replace("-", "").replace(" ", "").upper()
    if ced_prest != cedula_token.upper():
        raise HTTPException(status_code=403, detail="No tiene permiso para este recibo.")
    doc = (getattr(pago, "numero_documento", None) or "").strip()
    refp = (getattr(pago, "referencia_pago", None) or "").strip()
    referencia = (doc or refp or f"Pago-{pago_id}")[:80]
    fp = getattr(pago, "fecha_pago", None)
    fecha_pago_display = fp.strftime("%d/%m/%Y %H:%M") if fp and hasattr(fp, "strftime") else "-"
    titular = (getattr(prestamo, "nombres", None) or "").strip() or "-"
    ced_tit = (getattr(prestamo, "cedula", None) or "").strip() or "-"
    ced_comp = (getattr(pago, "cedula_cliente", None) or "").strip() or "-"
    banco = (getattr(pago, "institucion_bancaria", None) or "").strip() or "-"
    num_op = (doc or refp or "-")[:100]
    moneda_raw = (getattr(pago, "moneda_registro", None) or "").strip().upper()
    es_bs = moneda_raw in ("BS", "BOLIVAR", "BOLIVARES")
    monto_usd = float(getattr(pago, "monto_pagado", 0) or 0)
    monto_bs_val = getattr(pago, "monto_bs_original", None)
    tasa_val = getattr(pago, "tasa_cambio_bs_usd", None)
    if es_bs and monto_bs_val is not None:
        monto_pagado_texto = f"{_formato_monto_venezolano(float(monto_bs_val))} Bs."
        tf = float(tasa_val) if tasa_val is not None else None
        nota_moneda = (
            f"Equivalente en cartera: <b>{_formato_monto_venezolano(monto_usd)} USD</b>."
            + (f" Tasa Bs/USD del registro: {tf:,.6f}." if tf else "")
        )
    else:
        monto_pagado_texto = f"{_formato_monto_venezolano(monto_usd)} USD"
        nota_moneda = "Monto reconocido en cartera en dolares estadounidenses (USD)."
    filas = desglose_aplicacion_cuotas_por_pago(db, pago_id)
    pdf_bytes = generar_recibo_pago_cartera_pdf(
        referencia_documento=referencia,
        fecha_pago_display=fecha_pago_display,
        titular_credito=titular,
        cedula_titular=ced_tit,
        cedula_comprobante=ced_comp,
        banco=banco,
        numero_operacion=num_op,
        monto_pagado_texto=monto_pagado_texto,
        nota_moneda=nota_moneda,
        filas_aplicacion=filas,
    )
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_pago_{pago_id}.pdf"'},
    )


'''
anchor = '\n\n\n@router.get("/validar-cedula", response_model=ValidarCedulaEstadoCuentaResponse)\n'
if anchor not in t:
    raise SystemExit("validar-cedula anchor not found")
if "/recibo-pago" not in t:
    t = t.replace(anchor, route + anchor, 1)

# PDF: recibos=[] en verificar e informes
t = t.replace(
    "        recibos = obtener_recibos_cliente_estado_cuenta(db, cedula_lookup)\n\n        recibo_token = create_recibo_token(cedula_lookup, expire_hours=2)\n\n        base_url = str(request.base_url).rstrip(\"/\")\n\n        pdf_bytes = generar_pdf_estado_cuenta(",
    "        recibos = []\n\n        recibo_token = create_recibo_token(cedula_lookup, expire_hours=2)\n\n        base_url = str(request.base_url).rstrip(\"/\")\n\n        pdf_bytes = generar_pdf_estado_cuenta(",
    1,
)
t = t.replace(
    "    recibos = obtener_recibos_cliente_estado_cuenta(db, cedula_lookup)\n\n    base_url = str(request.base_url).rstrip(\"/\")\n\n    recibo_token = create_recibo_token(cedula_lookup, expire_hours=2)\n\n    pdf_bytes = generar_pdf_estado_cuenta(",
    "    recibos = []\n\n    base_url = str(request.base_url).rstrip(\"/\")\n\n    recibo_token = create_recibo_token(cedula_lookup, expire_hours=2)\n\n    pdf_bytes = generar_pdf_estado_cuenta(",
    1,
)

ep.write_text(t, encoding="utf-8")
print("patched", ep)

# estado_cuenta_pdf.py
pdfp = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
pt = pdfp.read_text(encoding="utf-8")
old_block = """    # ----- Pagos realizados (recibos) -----
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
        story.append(Spacer(1, 12))"""

new_block = """    # ----- Pagos realizados (recibo por pago de cartera) -----
    pagos_realizados = pagos_realizados or []
    if pagos_realizados and base_url and recibo_token:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Pagos realizados (recibos)", styles["SectionTitle"]))
        style_link = ParagraphStyle(
            name="ReciboPagoLink",
            fontSize=9,
            textColor=COLOR_HEADER,
            spaceAfter=2,
        )
        rows = [["Documento / ref.", "Fecha pago", "Monto pagado", "Recibo"]]
        for r in pagos_realizados:
            ref = (r.get("referencia_tabla") or str(r.get("pago_id") or ""))[:26]
            fecha = (r.get("fecha_pago_display") or "-")[:22]
            monto = (r.get("monto_display") or "-")[:28]
            pid = r.get("pago_id")
            if pid:
                url = f"{base_url}/api/v1/estado-cuenta/public/recibo-pago?token={recibo_token}&pago_id={pid}"
                link_cell = Paragraph(f'<a href="{url}" color="{COLOR_HEADER}">Ver recibo</a>', style_link)
            else:
                link_cell = Paragraph("&mdash;", style_link)
            rows.append([ref, fecha, monto, link_cell])
        t = Table(rows, colWidths=[108, 92, 92, 72])
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
                ("FONTSIZE", (0, 1), (-1, -1), 8),
            ])
        )
        story.append(t)
        story.append(Spacer(1, 12))
    recibos = recibos or []
    if recibos and base_url and not pagos_realizados:
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
        t2 = Table(rows, colWidths=[100, 70, 85, 75])
        t2.setStyle(
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
        story.append(t2)
        story.append(Spacer(1, 12))"""

if old_block not in pt:
    raise SystemExit("old pdf block not found")
pdfp.write_text(pt.replace(old_block, new_block, 1), encoding="utf-8")
print("patched", pdfp)
