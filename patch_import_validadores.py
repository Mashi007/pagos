# -*- coding: utf-8 -*-
"""Añade validación de cédula (igual que Pagos desde Excel) en Importar reportados aprobados."""
path = "backend/app/api/v1/endpoints/pagos.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """            errores_detalle.append({"referencia": pr.referencia_interna, "error": "Cédula vacía"})
            continue

        numero_doc_raw = (pr.referencia_interna or "").strip()[:100]"""

# Try with accented chars as in file (might be stored differently)
for err_blank in ("Cédula vacía", "Cdula vaca", "C\u00e9dula vac\u00eda"):
    for doc_line in (
        '        numero_doc_raw = (pr.referencia_interna or "").strip()[:100]',
        "        numero_doc_raw = (pr.referencia_interna or \"\").strip()[:100]",
    ):
        candidate = f"""            errores_detalle.append({{"referencia": pr.referencia_interna, "error": "{err_blank}"}})
            continue

{doc_line}"""
        if candidate in content:
            new = f"""            errores_detalle.append({{"referencia": pr.referencia_interna, "error": "{err_blank}"}})
            continue

        # Mismo validador que Pagos desde Excel: cédula V/E/J + 6-11 dígitos
        if not _looks_like_cedula_inline(cedula_raw):
            ref = (pr.referencia_interna or "").strip()[:100] or "N/A"
            pce = PagoConError(
                cedula_cliente=cedula_raw,
                prestamo_id=None,
                fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),
                monto_pagado=float(pr.monto or 0),
                numero_documento=(pr.referencia_interna or "")[:100],
                estado="PENDIENTE",
                referencia_pago=ref,
                errores_descripcion=["Cédula inválida. Formato: V, E o J + 6-11 dígitos (igual que Pagos desde Excel)."],
                observaciones=ORIGEN_COBROS_REPORTADOS,
                fila_origen=pr.id,
            )
            db.add(pce)
            db.flush()
            ids_pagos_con_errores.append(pce.id)
            errores_detalle.append({{"referencia": pr.referencia_interna, "error": "Cédula inválida (V/E/J + 6-11 dígitos)"}})
            continue

{doc_line}"""
            content = content.replace(candidate, new, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print("OK: parche aplicado.")
            exit(0)

# Fallback: search by unique context
marker = '            continue\n\n        numero_doc_raw = (pr.referencia_interna or "").strip()[:100]'
if marker in content:
    insert = '''            continue

        # Mismo validador que Pagos desde Excel: cedula V/E/J + 6-11 digitos
        if not _looks_like_cedula_inline(cedula_raw):
            ref = (pr.referencia_interna or "").strip()[:100] or "N/A"
            pce = PagoConError(
                cedula_cliente=cedula_raw,
                prestamo_id=None,
                fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),
                monto_pagado=float(pr.monto or 0),
                numero_documento=(pr.referencia_interna or "")[:100],
                estado="PENDIENTE",
                referencia_pago=ref,
                errores_descripcion=["Cedula invalida. Formato: V, E o J + 6-11 digitos (igual que Pagos desde Excel)."],
                observaciones=ORIGEN_COBROS_REPORTADOS,
                fila_origen=pr.id,
            )
            db.add(pce)
            db.flush()
            ids_pagos_con_errores.append(pce.id)
            errores_detalle.append({"referencia": pr.referencia_interna, "error": "Cedula invalida (V/E/J + 6-11 digitos)"})
            continue

        numero_doc_raw = (pr.referencia_interna or "").strip()[:100]'''
    content = content.replace(marker, insert, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: parche aplicado (fallback).")
    exit(0)

print("No se encontro el punto de insercion.")
exit(1)
