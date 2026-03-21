# -*- coding: utf-8 -*-
"""Incluye estado de cuota (reglas Caracas) en recibos PDF. Ejecutar: python backend/scripts/apply_recibo_estado_cuota.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch_cuota_estado() -> None:
    path = ROOT / "backend" / "app" / "services" / "cuota_estado.py"
    t = path.read_text(encoding="utf-8")
    if "def etiqueta_estado_cuota" in t:
        return
    needle = (
        "    return clasificar_estado_cuota(\n"
        "        total_pagado, monto_cuota, fecha_vencimiento, fecha_referencia\n"
        "    )\n\n# SQL PostgreSQL"
    )
    repl = (
        "    return clasificar_estado_cuota(\n"
        "        total_pagado, monto_cuota, fecha_vencimiento, fecha_referencia\n"
        "    )\n\n\n"
        "def etiqueta_estado_cuota(codigo: str) -> str:\n"
        '    """Texto para UI/PDF (misma nomenclatura que la tabla de amortizacion en frontend)."""\n'
        '    c = (codigo or "").strip().upper()\n'
        "    labels = {\n"
        '        "PENDIENTE": "Pendiente",\n'
        '        "PARCIAL": "Pendiente parcial",\n'
        '        "VENCIDO": "Vencido (1-91 d)",\n'
        '        "MORA": "Mora (92+ d)",\n'
        '        "PAGADO": "Pagado",\n'
        '        "PAGO_ADELANTADO": "Pago adelantado",\n'
        '        "PAGADA": "Pagado",\n'
        "    }\n"
        "    return labels.get(c, codigo.strip() if codigo else \"-\")\n\n\n"
        "# SQL PostgreSQL"
    )
    if needle not in t:
        raise SystemExit("cuota_estado.py: anchor missing")
    path.write_text(t.replace(needle, repl), encoding="utf-8", newline="\n")


def patch_recibo_pdf() -> None:
    path = ROOT / "backend" / "app" / "services" / "cobros" / "recibo_pdf.py"
    t = path.read_text(encoding="utf-8")
    sig = t.split("def generar_recibo_pago_reportado", 1)[1][:900]
    if "estado_cuota: Optional[str] = None" not in sig:
        t = t.replace(
            "    moneda: Optional[str] = None,\n"
            "    tasa_cambio: Optional[float] = None,\n"
            ") -> bytes:",
            "    moneda: Optional[str] = None,\n"
            "    tasa_cambio: Optional[float] = None,\n"
            "    estado_cuota: Optional[str] = None,\n"
            ") -> bytes:",
        )

    if "estado_cuota_lbl" not in t:
        t = t.replace(
            '    cuotas_txt = (aplicado_a_cuotas or "").strip() or "Pendiente de aplicar"\n\n    # Simbolo de moneda',
            '    cuotas_txt = (aplicado_a_cuotas or "").strip() or "Pendiente de aplicar"\n'
            '    estado_cuota_lbl = ((estado_cuota or "").strip() or None)\n\n    # Simbolo de moneda',
        )

    old_block = """        [
            Paragraph("Aplicado a", label_style),
            Paragraph(f"<b>{cuotas_txt}</b>", value_style),
            Paragraph("", label_style),
            Paragraph("", value_style),
        ],
    ]

    table = Table(info, colWidths=[1.45 * inch, 2.0 * inch, 1.2 * inch, 1.45 * inch])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))"""

    new_block = """        [
            Paragraph("Aplicado a", label_style),
            Paragraph(f"<b>{cuotas_txt}</b>", value_style),
            Paragraph("", label_style),
            Paragraph("", value_style),
        ],
    ]
    if estado_cuota_lbl:
        info.append(
            [
                Paragraph("Estado (cuota)", label_style),
                Paragraph(f"<b>{estado_cuota_lbl}</b>", value_style),
                Paragraph("", label_style),
                Paragraph("", value_style),
            ]
        )

    _info_style = [
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if estado_cuota_lbl:
        _info_style.append(
            ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#f8fafc")),
        )

    table = Table(info, colWidths=[1.45 * inch, 2.0 * inch, 1.2 * inch, 1.45 * inch])
    table.setStyle(TableStyle(_info_style))"""

    if old_block in t:
        t = t.replace(old_block, new_block)
    elif "_info_style" in t:
        print("recibo_pdf: info table already patched")
    else:
        raise SystemExit("recibo_pdf.py: info/table block not found")

    old_saldos = """        saldos_table = Table(
            [
                [
                    Paragraph("Cuota", label_style),
                    Paragraph("Saldo Inicial", label_style),
                    Paragraph("Abono", label_style),
                    Paragraph("Fecha de Pago", label_style),
                    Paragraph("Saldo Final", label_style),
                ],
                [
                    Paragraph(f"<b>{cuota_num_display}</b>", value_style),
                    Paragraph(f"{saldo_init_display} {moneda_symbol}" if saldo_init_display != "-" else "-", value_style),
                    Paragraph(f"<b>{monto_abono} {moneda_symbol}</b>" if monto_abono != "-" else "-", value_style),
                    Paragraph(fecha_pago_col, value_style),
                    Paragraph(f"{saldo_fin_display} {moneda_symbol}" if saldo_fin_display != "-" else "-", value_style),
                ],
            ],
            colWidths=[0.8 * inch, 1.3 * inch, 1.2 * inch, 1.3 * inch, 1.3 * inch],
        )"""

    new_saldos = """        _estado_cell = estado_cuota_lbl or "-"
        saldos_table = Table(
            [
                [
                    Paragraph("Cuota", label_style),
                    Paragraph("Saldo Inicial", label_style),
                    Paragraph("Abono", label_style),
                    Paragraph("Fecha de Pago", label_style),
                    Paragraph("Saldo Final", label_style),
                    Paragraph("Estado", label_style),
                ],
                [
                    Paragraph(f"<b>{cuota_num_display}</b>", value_style),
                    Paragraph(f"{saldo_init_display} {moneda_symbol}" if saldo_init_display != "-" else "-", value_style),
                    Paragraph(f"<b>{monto_abono} {moneda_symbol}</b>" if monto_abono != "-" else "-", value_style),
                    Paragraph(fecha_pago_col, value_style),
                    Paragraph(f"{saldo_fin_display} {moneda_symbol}" if saldo_fin_display != "-" else "-", value_style),
                    Paragraph(_estado_cell, value_style),
                ],
            ],
            colWidths=[0.65 * inch, 1.05 * inch, 1.0 * inch, 1.05 * inch, 1.05 * inch, 1.15 * inch],
        )"""

    if old_saldos in t:
        t = t.replace(old_saldos, new_saldos)
    elif "_estado_cell" in t:
        print("recibo_pdf: saldos table already patched")
    else:
        raise SystemExit("recibo_pdf.py: saldos_table block not found")

    path.write_text(t, encoding="utf-8", newline="\n")


def patch_recibo_cuota_wrapper() -> None:
    path = ROOT / "backend" / "app" / "services" / "cobros" / "recibo_cuota_amortizacion.py"
    t = path.read_text(encoding="utf-8")
    if "estado_cuota: Optional[str] = None" in t:
        return
    t = t.replace(
        "    moneda: Optional[str] = None,\n) -> bytes:",
        "    moneda: Optional[str] = None,\n    estado_cuota: Optional[str] = None,\n) -> bytes:",
    )
    t = t.replace(
        "        fecha_pago_display=fecha_pago_display,\n        moneda=moneda,\n    )",
        "        fecha_pago_display=fecha_pago_display,\n        moneda=moneda,\n        estado_cuota=estado_cuota,\n    )",
    )
    path.write_text(t, encoding="utf-8", newline="\n")


def patch_prestamos_endpoint() -> None:
    path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
    t = path.read_text(encoding="utf-8")
    if "etiqueta_estado_cuota" not in t:
        t = t.replace(
            "from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio",
            "from app.services.cuota_estado import (\n    estado_cuota_para_mostrar,\n    etiqueta_estado_cuota,\n    hoy_negocio,\n)",
        )

    if "estado_cuota_lbl" in t and "estado_cuota=estado_cuota_lbl" in t:
        print("prestamos: already patched")
        path.write_text(t, encoding="utf-8", newline="\n")
        return

    lines = t.splitlines()
    i = next(
        idx
        for idx, line in enumerate(lines)
        if "pdf_bytes = generar_recibo_cuota_amortizacion" in line
    )
    j = i
    while j < len(lines):
        if lines[j].strip() == ")" and lines[j].startswith("    "):
            break
        j += 1
    old_snip = "\n".join(lines[i : j + 1])

    prefix = """
    fv_c = cuota.fecha_vencimiento

    fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

    estado_codigo = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date_c, hoy_negocio())

    estado_cuota_lbl = etiqueta_estado_cuota(estado_codigo)

    saldo_ini_s = f"{float(cuota.saldo_capital_inicial or 0):.2f}" if cuota.saldo_capital_inicial is not None else "-"

    saldo_fin_s = f"{float(cuota.saldo_capital_final or 0):.2f}" if cuota.saldo_capital_final is not None else "-"

    fpd = "-"

    if fecha_pago_date:

        fpd = fecha_pago_date.strftime("%d/%m/%Y")

""".lstrip("\n")

    new_call = """    pdf_bytes = generar_recibo_cuota_amortizacion(

        referencia_interna=referencia,

        nombres_completos=(prestamo.nombres or "").strip(),

        cedula=(prestamo.cedula or "").strip(),

        institucion_financiera=institucion,

        monto=monto_str,

        numero_operacion=numero_operacion,

        fecha_recepcion=fecha_recep,

        fecha_pago=fecha_pago_date,

        moneda="Bs.",

        aplicado_a_cuotas=f"Cuota {cuota.numero_cuota}",

        saldo_inicial=saldo_ini_s,

        saldo_final=saldo_fin_s,

        numero_cuota=cuota.numero_cuota,

        fecha_pago_display=fpd,

        estado_cuota=estado_cuota_lbl,

    )"""

    t = t.replace(old_snip, prefix + new_call)
    path.write_text(t, encoding="utf-8", newline="\n")


def main() -> None:
    patch_cuota_estado()
    patch_recibo_pdf()
    patch_recibo_cuota_wrapper()
    patch_prestamos_endpoint()
    print("done")


if __name__ == "__main__":
    main()
