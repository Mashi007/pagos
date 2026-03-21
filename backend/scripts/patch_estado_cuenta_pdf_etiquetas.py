# -*- coding: utf-8 -*-
"""PDF estado de cuenta: estados con etiquetas como tabla amortizacion; quita CONCILIADO."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
t = path.read_text(encoding="utf-8")

if "from app.services.cuota_estado import etiqueta_estado_cuota" not in t:
    t = t.replace(
        'from typing import List, Optional\n\n\n\n# Ruta al logo',
        "from typing import List, Optional\n\nfrom app.services.cuota_estado import etiqueta_estado_cuota\n\n\n# Ruta al logo",
    )

# Cuotas pendientes: etiqueta en vez de codigo truncado
old_pend = """            rows.append(

                [

                    str(c.get("prestamo_id", "")),

                    str(c.get("numero_cuota", "")),

                    fv,

                    f"{float(c.get('monto') or 0):,.2f}",

                    (c.get("estado") or "")[:12],

                ]

            )"""
new_pend = """            rows.append(

                [

                    str(c.get("prestamo_id", "")),

                    str(c.get("numero_cuota", "")),

                    fv,

                    f"{float(c.get('monto') or 0):,.2f}",

                    etiqueta_estado_cuota(str(c.get("estado") or ""))[:28],

                ]

            )"""
if old_pend in t:
    t = t.replace(old_pend, new_pend)
elif "etiqueta_estado_cuota(str(c.get(\"estado\")" in t:
    print("pendientes: skip")
else:
    raise SystemExit("block pendientes not found")

# Amortizacion: etiqueta + recibo para PAGADO y PAGO_ADELANTADO
old_amort = """            for c in cuotas:

                estado_cuota = (c.get("estado") or "").strip().upper()

                cuota_id = c.get("id")

                puede_recibo = estado_cuota == "PAGADO" and cuota_id and base_url and recibo_token

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

                        (c.get("estado") or "")[:10],

                        recibo_cell,

                    ]

                )"""
new_amort = """            for c in cuotas:

                estado_codigo = (c.get("estado") or "").strip().upper()

                estado_etiqueta = etiqueta_estado_cuota(c.get("estado") or "")

                cuota_id = c.get("id")

                puede_recibo = (

                    estado_codigo in ("PAGADO", "PAGO_ADELANTADO")

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

                )"""
if old_amort in t:
    t = t.replace(old_amort, new_amort)
elif "estado_etiqueta = etiqueta_estado_cuota" in t:
    print("amort: skip")
else:
    raise SystemExit("block amort not found")

# Ancho columna Estado en amortizacion
t = t.replace(
    "colWidths=[34, 48, 48, 44, 48, 48, 48, 46, 52],",
    "colWidths=[32, 46, 44, 40, 46, 44, 44, 58, 50],",
)

# obtener_datos: quitar CONCILIADO
old_obt = """                estado_backend = (getattr(c, "estado", "") or "").strip().upper()

                fv_c = getattr(c, "fecha_vencimiento", None)

                fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

                

                if estado_backend == "PAGADO" and pago_conciliado:

                    estado_cuota = "CONCILIADO"

                else:

                    estado_cuota = estado_cuota_para_mostrar(total_pagado_c, monto_c, fv_date_c, fecha_corte_dt)

                

                pago_conc_display = "Si" if pago_conciliado else "-"
"""
new_obt = """                fv_c = getattr(c, "fecha_vencimiento", None)

                fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

                estado_cuota = estado_cuota_para_mostrar(

                    total_pagado_c, monto_c, fv_date_c, fecha_corte_dt

                )

                pago_conc_display = "Si" if pago_conciliado else "-"
"""
if old_obt in t:
    t = t.replace(old_obt, new_obt)
elif 'estado_cuota = estado_cuota_para_mostrar(\n\n                    total_pagado_c, monto_c, fv_date_c, fecha_corte_dt\n\n                )' in t:
    print("obtener_datos: skip")
else:
    # try without extra blank lines
    raise SystemExit("obtener_datos block not found")

# Remove unused estado_backend if loop still has pago_conciliado - need to check loop still defines pago_conciliado
if "pago_conciliado = getattr(c, \"pago_conciliado\", False)" not in t:
    raise SystemExit("pago_conciliado line missing")

path.write_text(t, encoding="utf-8", newline="\n")
print("ok")
