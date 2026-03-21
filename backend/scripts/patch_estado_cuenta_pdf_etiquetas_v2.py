# -*- coding: utf-8 -*-
"""PDF estado de cuenta publico: etiquetas de estado como en tabla amortizacion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
t = path.read_text(encoding="utf-8")

if "from app.services.cuota_estado import etiqueta_estado_cuota" not in t:
    t = t.replace(
        "from typing import List, Optional\n\n\n\n# Ruta al logo",
        "from typing import List, Optional\n\nfrom app.services.cuota_estado import etiqueta_estado_cuota\n\n\n# Ruta al logo",
    )

old_pend = """                    (c.get("estado") or "")[:12],"""
new_pend = """                    etiqueta_estado_cuota(str(c.get("estado") or ""))[:28],"""
if old_pend in t:
    t = t.replace(old_pend, new_pend, 1)
elif "etiqueta_estado_cuota(str(c.get(\"estado\")" in t:
    print("pendientes: already")
else:
    raise SystemExit("pendientes marker missing")

old_amort_loop = """            for c in cuotas:

                estado_cuota = (c.get("estado") or "").strip().upper()

                cuota_id = c.get("id")

                puede_recibo = estado_cuota == "PAGADO" and cuota_id and base_url and recibo_token"""
new_amort_loop = """            for c in cuotas:

                estado_codigo = (c.get("estado") or "").strip().upper()

                estado_etiqueta = etiqueta_estado_cuota(c.get("estado") or "")

                cuota_id = c.get("id")

                puede_recibo = (

                    estado_codigo in ("PAGADO", "PAGO_ADELANTADO")

                    and cuota_id

                    and base_url

                    and recibo_token

                )"""
if old_amort_loop in t:
    t = t.replace(old_amort_loop, new_amort_loop, 1)
elif "estado_etiqueta = etiqueta_estado_cuota" in t:
    print("amort loop: already")
else:
    raise SystemExit("amort loop marker missing")

old_cell = """                        (c.get("estado") or "")[:10],"""
new_cell = """                        estado_etiqueta[:22],"""
if old_cell in t:
    t = t.replace(old_cell, new_cell, 1)
elif "estado_etiqueta[:22]" in t:
    print("amort cell: already")
else:
    raise SystemExit("amort cell marker missing")

old_cw = "colWidths=[34, 48, 48, 44, 48, 48, 48, 46, 52],"
new_cw = "colWidths=[32, 46, 44, 40, 46, 44, 44, 58, 50],"
if old_cw in t:
    t = t.replace(old_cw, new_cw, 1)
elif new_cw in t:
    print("colwidths: already")
else:
    raise SystemExit("colwidths missing")

old_conc = """                estado_backend = (getattr(c, "estado", "") or "").strip().upper()

                fv_c = getattr(c, "fecha_vencimiento", None)

                fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

                

                if estado_backend == "PAGADO" and pago_conciliado:

                    estado_cuota = "CONCILIADO"

                else:

                    estado_cuota = estado_cuota_para_mostrar(total_pagado_c, monto_c, fv_date_c, fecha_corte_dt)

                
"""
new_conc = """                fv_c = getattr(c, "fecha_vencimiento", None)

                fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

                estado_cuota = estado_cuota_para_mostrar(total_pagado_c, monto_c, fv_date_c, fecha_corte_dt)

                
"""
if old_conc in t:
    t = t.replace(old_conc, new_conc, 1)
elif "CONCILIADO" not in t:
    print("obtener_datos: already")
else:
    raise SystemExit("CONCILIADO block missing or file changed")

path.write_text(t, encoding="utf-8", newline="\n")
print("ok")
