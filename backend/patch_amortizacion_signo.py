# Reporte contable: todas las cuotas por vencimiento; con pago +, sin pago -
# Ejecutar desde raiz: python backend/patch_amortizacion_signo.py
import re
path = "backend/app/api/v1/endpoints/reportes/reportes_contable.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Insertar _query_cuotas_por_vencimiento despues de "return db.execute(q).fetchall()" de _query_cuotas_contable
#    (primera ocurrencia que esta dentro de _query_cuotas_contable)
insert_after_query = """    return db.execute(q).fetchall()


def _query_cuotas_por_vencimiento(db: Session, fecha_inicio: date, fecha_fin: date):
    \"\"\"Todas las cuotas con fecha_vencimiento en el rango (amortizacion). LEFT JOIN pagos.\"\"\"
    prestamo_valido = and_(Cuota.prestamo_id.isnot(None), Prestamo.id.isnot(None))
    rango_vencimiento = and_(
        Cuota.fecha_vencimiento >= fecha_inicio,
        Cuota.fecha_vencimiento <= fecha_fin,
    )
    if hasattr(Cuota, "pago_id"):
        q = (
            select(
                Cuota.id,
                Cuota.numero_cuota,
                Cuota.fecha_vencimiento,
                Cuota.fecha_pago,
                Cuota.monto,
                Cuota.total_pagado,
                Prestamo.cedula,
                Prestamo.nombres,
                Pago.fecha_pago.label("fecha_pago_real"),
                Pago.monto_pagado.label("monto_pagado_real"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(Pago, Cuota.pago_id == Pago.id)
            .where(and_(prestamo_valido, rango_vencimiento))
        )
    else:
        q = (
            select(
                Cuota.id,
                Cuota.numero_cuota,
                Cuota.fecha_vencimiento,
                Cuota.fecha_pago,
                Cuota.monto,
                Cuota.monto.label("total_pagado"),
                Prestamo.cedula,
                Prestamo.nombres,
                Cuota.fecha_pago.label("fecha_pago_real"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(and_(prestamo_valido, rango_vencimiento))
        )
        q = q.add_columns(None.label("monto_pagado_real"))
    return db.execute(q).fetchall()
"""

# Find the exact return in _query_cuotas_contable (the one followed by sync_reporte)
marker = "    return db.execute(q).fetchall()\n\n\ndef sync_reporte_contable_completo"
if marker in content:
    content = content.replace(
        marker,
        "    return db.execute(q).fetchall()\n\n\ndef _query_cuotas_por_vencimiento(db: Session, fecha_inicio: date, fecha_fin: date):\n"
        '    """Todas las cuotas con fecha_vencimiento en el rango (amortizacion). LEFT JOIN pagos."""\n'
        "    prestamo_valido = and_(Cuota.prestamo_id.isnot(None), Prestamo.id.isnot(None))\n"
        "    rango_vencimiento = and_(\n"
        "        Cuota.fecha_vencimiento >= fecha_inicio,\n"
        "        Cuota.fecha_vencimiento <= fecha_fin,\n"
        "    )\n"
        "    if hasattr(Cuota, \"pago_id\"):\n"
        "        q = (\n"
        "            select(\n"
        "                Cuota.id, Cuota.numero_cuota, Cuota.fecha_vencimiento, Cuota.fecha_pago,\n"
        "                Cuota.monto, Cuota.total_pagado, Prestamo.cedula, Prestamo.nombres,\n"
        "                Pago.fecha_pago.label(\"fecha_pago_real\"), Pago.monto_pagado.label(\"monto_pagado_real\"),\n"
        "            )\n"
        "            .select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n"
        "            .outerjoin(Pago, Cuota.pago_id == Pago.id)\n"
        "            .where(and_(prestamo_valido, rango_vencimiento))\n"
        "        )\n"
        "    else:\n"
        "        q = (\n"
        "            select(\n"
        "                Cuota.id, Cuota.numero_cuota, Cuota.fecha_vencimiento, Cuota.fecha_pago,\n"
        "                Cuota.monto, Cuota.monto.label(\"total_pagado\"), Prestamo.cedula, Prestamo.nombres,\n"
        "                Cuota.fecha_pago.label(\"fecha_pago_real\"),\n"
        "            )\n"
        "            .select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n"
        "            .where(and_(prestamo_valido, rango_vencimiento))\n"
        "        )\n"
        "    return db.execute(q).fetchall()\n\n\ndef sync_reporte_contable_completo"
    )
    print("1) _query_cuotas_por_vencimiento inserted")
else:
    print("1) marker not found")

# 2) Insertar _cuotas_a_filas_contable_con_signo despues de _cuotas_a_filas_contable (despues de "return items")
marker2 = "        })\n    return items\n\n\ndef _query_cuotas_contable"
if "def _cuotas_a_filas_contable_con_signo" not in content and marker2 in content:
    signo_func = '''
def _cuotas_a_filas_contable_con_signo(rows, tasas_cache: dict) -> List[dict]:
    """Todas las cuotas: con pago en tabla pagos -> Importe MD positivo; sin pago -> negativo (no pago)."""
    items: List[dict] = []
    for r in rows:
        monto_cuota = _safe_float(r.monto)
        monto_pago_real = getattr(r, "monto_pagado_real", None)
        try:
            tiene_pago = monto_pago_real is not None and _safe_float(monto_pago_real) > 0
        except (TypeError, ValueError):
            tiene_pago = False

        if tiene_pago:
            importe_md = round(_safe_float(monto_pago_real), 2)
            fp = getattr(r, "fecha_pago_real", None) or r.fecha_pago
            fp_date = fp.date() if hasattr(fp, "date") else (date.fromisoformat(str(fp)[:10]) if fp else None)
            tipo_doc = f"Cuota {r.numero_cuota}"
        else:
            importe_md = round(-monto_cuota, 2)
            fp_date = None
            tipo_doc = f"Cuota {r.numero_cuota} (no pago)"

        fv = r.fecha_vencimiento
        if fp_date is not None:
            if fp_date not in tasas_cache:
                tasas_cache[fp_date] = _obtener_tasa_usd_bs(fp_date)
            tasa = tasas_cache[fp_date]
        else:
            if fv not in tasas_cache:
                tasas_cache[fv] = _obtener_tasa_usd_bs(fv)
            tasa = tasas_cache[fv]
        importe_ml = round(importe_md * tasa, 2)

        items.append({
            "cuota_id": r.id,
            "cedula": r.cedula or "",
            "nombre": (r.nombres or "").strip(),
            "tipo_documento": tipo_doc,
            "fecha_vencimiento": fv,
            "fecha_pago": fp_date,
            "importe_md": importe_md,
            "moneda_documento": "USD",
            "tasa": tasa,
            "importe_ml": importe_ml,
            "moneda_local": "Bs.",
        })
    return items

'''
    content = content.replace(marker2, "        })\n    return items\n" + signo_func + "\ndef _query_cuotas_contable")
    print("2) _cuotas_a_filas_contable_con_signo inserted")
else:
    if "def _cuotas_a_filas_contable_con_signo" in content:
        print("2) already present")
    else:
        print("2) marker2 not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done. Now update exportar_contable to use _query_cuotas_por_vencimiento + _cuotas_a_filas_contable_con_signo.")
