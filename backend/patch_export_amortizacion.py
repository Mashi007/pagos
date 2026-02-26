# Hacer que exportar_contable use siempre todas las cuotas por vencimiento con signo +/-
path = "backend/app/api/v1/endpoints/reportes/reportes_contable.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Reemplazar: obtener datos desde cache + fallback si vacio, por: siempre consulta por vencimiento con signo
old = """    cedulas_list = None
    if cedulas and cedulas.strip():
        cedulas_list = [c.strip() for c in cedulas.split(",") if c.strip()]

    data = get_reporte_contable_desde_cache(db, anos=anos_list, meses=meses_list, cedulas=cedulas_list)
    items = data.get("items", [])
    # Si el cache no tiene datos para el periodo, consultar en vivo (p. ej. cache vacio o desactualizado)
    if not items and anos_list and meses_list:
        periodos = [(a, m) for a in anos_list for m in meses_list]
        if periodos:
            min_p = min(periodos, key=lambda p: (p[0], p[1]))
            max_p = max(periodos, key=lambda p: (p[0], p[1]))
            fi = date(min_p[0], min_p[1], 1)
            _, ult = calendar.monthrange(max_p[0], max_p[1])
            ff = date(max_p[0], max_p[1], ult)
            rows = _query_cuotas_contable(db, fi, ff)
            tasas_fb = {}
            filas_fb = _cuotas_a_filas_contable(rows, tasas_fb)
            if cedulas_list:
                filas_fb = [f for f in filas_fb if f["cedula"] in cedulas_list]
            items = [
                {
                    "cedula": f["cedula"],
                    "nombre": f["nombre"],
                    "tipo_documento": f["tipo_documento"],
                    "fecha_vencimiento": f["fecha_vencimiento"].isoformat() if hasattr(f.get("fecha_vencimiento"), "isoformat") else str(f.get("fecha_vencimiento", "")),
                    "fecha_pago": f["fecha_pago"].isoformat() if hasattr(f.get("fecha_pago"), "isoformat") else str(f.get("fecha_pago", "")),
                    "importe_md": _safe_float(f.get("importe_md")),
                    "moneda_documento": f.get("moneda_documento") or "USD",
                    "tasa": _safe_float(f.get("tasa")),
                    "importe_ml": _safe_float(f.get("importe_ml")),
                    "moneda_local": f.get("moneda_local") or "Bs.",
                }
                for f in filas_fb
            ]
            data = {"items": items, "fecha_inicio": fi.isoformat(), "fecha_fin": ff.isoformat()}
    content = _generar_excel_contable(data)"""

new = """    cedulas_list = None
    if cedulas and cedulas.strip():
        cedulas_list = [c.strip() for c in cedulas.split(",") if c.strip()]

    # Todas las cuotas con vencimiento en el periodo: con pago -> Importe MD +; sin pago -> -
    periodos = [(a, m) for a in anos_list for m in meses_list]
    if not periodos:
        data = {"items": [], "fecha_inicio": "", "fecha_fin": ""}
    else:
        min_p = min(periodos, key=lambda p: (p[0], p[1]))
        max_p = max(periodos, key=lambda p: (p[0], p[1]))
        fi = date(min_p[0], min_p[1], 1)
        _, ult = calendar.monthrange(max_p[0], max_p[1])
        ff = date(max_p[0], max_p[1], ult)
        rows = _query_cuotas_por_vencimiento(db, fi, ff)
        tasas_fb = {}
        filas_fb = _cuotas_a_filas_contable_con_signo(rows, tasas_fb)
        if cedulas_list:
            filas_fb = [f for f in filas_fb if f["cedula"] in cedulas_list]
        items = []
        for f in filas_fb:
            fv = f.get("fecha_vencimiento")
            fp = f.get("fecha_pago")
            items.append({
                "cedula": f["cedula"],
                "nombre": f["nombre"],
                "tipo_documento": f["tipo_documento"],
                "fecha_vencimiento": fv.isoformat() if hasattr(fv, "isoformat") else str(fv or ""),
                "fecha_pago": fp.isoformat() if fp and hasattr(fp, "isoformat") else str(fp or ""),
                "importe_md": _safe_float(f.get("importe_md")),
                "moneda_documento": f.get("moneda_documento") or "USD",
                "tasa": _safe_float(f.get("tasa")),
                "importe_ml": _safe_float(f.get("importe_ml")),
                "moneda_local": f.get("moneda_local") or "Bs.",
            })
        data = {"items": items, "fecha_inicio": fi.isoformat(), "fecha_fin": ff.isoformat()}
    content = _generar_excel_contable(data)"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: exportar_contable usa todas las cuotas por vencimiento con signo +/-")
else:
    print("Block not found - check indentation or content")
