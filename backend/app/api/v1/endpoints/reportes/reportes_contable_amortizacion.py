# Fragmentos para insertar en reportes_contable.py:
# 1) Nueva funcion _query_cuotas_por_vencimiento (tras _query_cuotas_contable)
# 2) Nueva funcion _cuotas_a_filas_contable_con_signo (tras _cuotas_a_filas_contable o antes de _query)
# 3) En exportar_contable: usar siempre esta fuente

QUERY_POR_VENCIMIENTO = '''
def _query_cuotas_por_vencimiento(db: Session, fecha_inicio: date, fecha_fin: date):
    """Todas las cuotas con fecha_vencimiento en el rango (tabla amortizacion). LEFT JOIN pagos."""
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
                None.label("monto_pagado_real"),
            )
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .where(and_(prestamo_valido, rango_vencimiento))
        )
    return db.execute(q).fetchall()
'''

FILAS_CON_SIGNO = '''
def _cuotas_a_filas_contable_con_signo(rows, tasas_cache: dict) -> List[dict]:
    """Todas las cuotas: con pago en tabla pagos -> Importe MD positivo; sin pago -> negativo (refleja no pago)."""
    items: List[dict] = []
    for r in rows:
        monto_cuota = _safe_float(r.monto)
        monto_pago_real = getattr(r, "monto_pagado_real", None)
        tiene_pago = monto_pago_real is not None and _safe_float(monto_pago_real) > 0

        if tiene_pago:
            importe_md = round(_safe_float(monto_pago_real), 2)
            fp = getattr(r, "fecha_pago_real", None) or r.fecha_pago
            fp_date = fp.date() if hasattr(fp, "date") else (date.fromisoformat(str(fp)[:10]) if fp else date.today())
            tipo_doc = f"Cuota {r.numero_cuota}"
        else:
            importe_md = round(-monto_cuota, 2)
            fp_date = None
            tipo_doc = f"Cuota {r.numero_cuota} (no pago)"

        if fp_date is not None and fp_date not in tasas_cache:
            tasas_cache[fp_date] = _obtener_tasa_usd_bs(fp_date)
        tasa = tasas_cache.get(fp_date) if fp_date else _obtener_tasa_usd_bs(r.fecha_vencimiento) if r.fecha_vencimiento else 36.0
        if fp_date is None and r.fecha_vencimiento and r.fecha_vencimiento not in tasas_cache:
            tasas_cache[r.fecha_vencimiento] = _obtener_tasa_usd_bs(r.fecha_vencimiento)
        if fp_date is None and r.fecha_vencimiento:
            tasa = tasas_cache.get(r.fecha_vencimiento, _obtener_tasa_usd_bs(r.fecha_vencimiento))
        importe_ml = round(importe_md * tasa, 2)

        items.append({
            "cuota_id": r.id,
            "cedula": r.cedula or "",
            "nombre": (r.nombres or "").strip(),
            "tipo_documento": tipo_doc,
            "fecha_vencimiento": r.fecha_vencimiento,
            "fecha_pago": fp_date,
            "importe_md": importe_md,
            "moneda_documento": "USD",
            "tasa": tasa,
            "importe_ml": importe_ml,
            "moneda_local": "Bs.",
        })
    return items
'''
