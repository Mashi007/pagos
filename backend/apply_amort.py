# -*- coding: utf-8 -*-
path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_loop = """        fecha_venc = getattr(cu, "fecha_vencimiento", None)
        resultado.append({
            "numero_cuota": getattr(cu, "numero_cuota", 0),
            "fecha_vencimiento": fecha_venc.isoformat() if fecha_venc else "",
            "monto_capital": monto_capital,
            "monto_interes": monto_interes,
            "monto_cuota": monto_cuota,
            "saldo_capital_final": saldo_final,
            "estado": getattr(cu, "estado", None) or "PENDIENTE",
        })"""

new_loop = """        fecha_venc = getattr(cu, "fecha_vencimiento", None)
        fecha_iso = fecha_venc.isoformat() if fecha_venc else ""
        total_pagado_val = getattr(cu, "total_pagado", None)
        try:
            pago_conciliado_display = f"{float(total_pagado_val):,.2f}" if total_pagado_val is not None and float(total_pagado_val) > 0 else "-"
        except (TypeError, ValueError):
            pago_conciliado_display = "-"
        try:
            from datetime import datetime as _dt
            fecha_ddmm = _dt.strptime(fecha_iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y") if len(fecha_iso) >= 10 else (fecha_iso or "")
        except Exception:
            fecha_ddmm = fecha_iso[:10] if fecha_iso else ""
        resultado.append({
            "numero_cuota": getattr(cu, "numero_cuota", 0),
            "fecha_vencimiento": fecha_ddmm,
            "monto_capital": monto_capital,
            "monto_interes": monto_interes,
            "monto_cuota": monto_cuota,
            "saldo_capital_final": saldo_final,
            "pago_conciliado_display": pago_conciliado_display,
            "estado": getattr(cu, "estado", None) or "PENDIENTE",
        })"""

if old_loop not in c:
    print("old_loop not found")
    exit(1)
c = c.replace(old_loop, new_loop, 1)

# Cabecera y filas tabla PDF
old_headers = ["""            rows = [["Cuota", "Fecha Venc.", "Capital", "Interés", "Total", "Saldo Pendiente", "Estado"]]""",
               """            rows = [["Cuota", "Fecha Venc.", "Capital", "Inters", "Total", "Saldo Pendiente", "Estado"]]"""]
new_header = """            # Mismo orden que Detalles del Préstamo > Tabla de Amortización (TablaAmortizacionPrestamo.tsx)
            rows = [["Cuota", "Fecha Vencimiento", "Capital", "Interés", "Total", "Saldo Pendiente", "Pago conciliado", "Estado"]]"""
for old in old_headers:
    if old in c:
        c = c.replace(old, new_header, 1)
        break
else:
    print("headers not found")
    exit(1)

old_append = """            for c in cuotas:
                rows.append([
                    str(c.get("numero_cuota", "")),
                    (c.get("fecha_vencimiento") or "")[:10],
                    f"{c.get('monto_capital', 0):,.2f}",
                    f"{c.get('monto_interes', 0):,.2f}",
                    f"{c.get('monto_cuota', 0):,.2f}",
                    f"{c.get('saldo_capital_final', 0):,.2f}",
                    c.get("estado", ""),
                ])"""
new_append = """            for c in cuotas:
                rows.append([
                    str(c.get("numero_cuota", "")),
                    (c.get("fecha_vencimiento") or ""),
                    f"{c.get('monto_capital', 0):,.2f}",
                    f"{c.get('monto_interes', 0):,.2f}",
                    f"{c.get('monto_cuota', 0):,.2f}",
                    f"{c.get('saldo_capital_final', 0):,.2f}",
                    c.get("pago_conciliado_display", "-"),
                    c.get("estado", ""),
                ])"""
c = c.replace(old_append, new_append, 1)

c = c.replace('("ALIGN", (2, 0), (5, -1), "RIGHT")', '("ALIGN", (2, 0), (6, -1), "RIGHT")', 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: estado_cuenta_publico amortization updated")
