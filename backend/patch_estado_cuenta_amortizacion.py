# Unificar formato tabla amortizacion con Detalles del Prestamo (TablaAmortizacionPrestamo.tsx)
# Orden: Cuota, Fecha Vencimiento, Capital, Interes, Total, Saldo Pendiente, Pago conciliado, Estado
path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) En _obtener_amortizacion_prestamo: agregar total_pagado como pago_conciliado_display y fecha en DD/MM/YYYY
old_obtener = """        resultado.append({
            "numero_cuota": getattr(cu, "numero_cuota", 0),
            "fecha_vencimiento": fecha_venc.isoformat() if fecha_venc else "",
            "monto_capital": monto_capital,
            "monto_interes": monto_interes,
            "monto_cuota": monto_cuota,
            "saldo_capital_final": saldo_final,
            "estado": getattr(cu, "estado", None) or "PENDIENTE",
        })"""
# format date DD/MM/YYYY for UI match
import re
def _fmt_fecha(iso_str):
    if not iso_str or len(iso_str) < 10:
        return iso_str or ""
    try:
        from datetime import datetime
        d = datetime.strptime(iso_str[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso_str[:10]

# We need to add the logic in the loop - total_pagado and format fecha
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
total_pagado_val = getattr(cu, "total_pagado", None)  # this is inside the loop, cu is the variable
# So we need to do string replace that adds total_pagado and pago_conciliado_display and changes fecha format
new_loop = """        fecha_venc = getattr(cu, "fecha_vencimiento", None)
        fecha_iso = fecha_venc.isoformat() if fecha_venc else ""
        total_pagado_val = getattr(cu, "total_pagado", None)
        pago_conciliado_display = f"{float(total_pagado_val):,.2f}" if total_pagado_val is not None and float(total_pagado_val) > 0 else "-"
        try:
            from datetime import datetime as _dt
            fecha_ddmm = _dt.strptime(fecha_iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y") if len(fecha_iso) >= 10 else fecha_iso
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

# 2) En _generar_pdf_estado_cuenta: cabeceras y filas igual que UI (Cuota, Fecha Vencimiento, Capital, Interes, Total, Saldo Pendiente, Pago conciliado, Estado)
old_table = """            rows = [["Cuota", "Fecha Venc.", "Capital", "Inters", "Total", "Saldo Pendiente", "Estado"]]"""
new_table = """            # Mismo orden que Detalles del Prestamo > Tabla de Amortizacion (TablaAmortizacionPrestamo.tsx)
            rows = [["Cuota", "Fecha Vencimiento", "Capital", "Interes", "Total", "Saldo Pendiente", "Pago conciliado", "Estado"]]"""
c = c.replace(old_table, new_table, 1)

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

# ALIGN columnas numericas: 2-6 (Capital, Interes, Total, Saldo Pendiente, Pago conciliado) a la derecha
old_align = '("ALIGN", (2, 0), (5, -1), "RIGHT")'
new_align = '("ALIGN", (2, 0), (6, -1), "RIGHT")'
c = c.replace(old_align, new_align, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: estado_cuenta_publico amortization format updated")
