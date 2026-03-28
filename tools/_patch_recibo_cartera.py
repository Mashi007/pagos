"""One-off patch: estado_cuenta_datos desglose + listar fields."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "backend" / "app" / "services" / "estado_cuenta_datos.py"
t = p.read_text(encoding="utf-8")
needle = "    return None\n\n\ndef listar_pagos_realizados_estado_cuenta"
if needle not in t:
    raise SystemExit("needle not found for desglose insert")
block = """


def desglose_aplicacion_cuotas_por_pago(db: Session, pago_id: int) -> List[dict]:
    \"\"\"CuotaPago por pago: monto aplicado a cada cuota vs monto de cuota (pago total puede ser mayor).\"\"\"
    rows = db.execute(
        select(Cuota, CuotaPago.monto_aplicado)
        .join(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(CuotaPago.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
    ).all()
    out: List[dict] = []
    for cuota, m_apl in rows:
        c = cuota[0] if hasattr(cuota, "__getitem__") else cuota
        apl_raw = m_apl[0] if hasattr(m_apl, "__getitem__") else m_apl
        m_cuota = float(getattr(c, "monto", 0) or 0)
        apl = float(apl_raw or 0)
        pct_n = (apl / m_cuota * 100.0) if m_cuota > 0.0001 else 0.0
        if abs(pct_n - round(pct_n)) < 0.051:
            pct_str = f"{int(round(pct_n))}%"
        else:
            pct_str = f"{pct_n:.1f}%".replace(".", ",")
        out.append(
            {
                "numero_cuota": int(getattr(c, "numero_cuota", 0) or 0),
                "monto_cuota": m_cuota,
                "monto_aplicado": apl,
                "porcentaje_cuota": pct_str,
            }
        )
    return out
"""
t = t.replace(needle, block + "\n\n\ndef listar_pagos_realizados_estado_cuenta", 1)

old_append = """        resultado.append(
            {
                "pago_id": pago_id,
                "prestamo_id": int(prestamo_id) if prestamo_id is not None else None,
                "banco": banco,
                "fecha_pago_display": _fmt_fecha_hora_pago_estado_cuenta(fp),
                "fecha_registro_display": _fmt_fecha_hora_pago_estado_cuenta(fr),
                "monto_display": monto_display,
                "tasa_display": tasa_display,
                "subtotal_usd": monto_usd,
                "es_bs": es_bs,
                "recibo_prestamo_id": rp,
                "recibo_cuota_id": rc,
            }
        )"""
new_append = """        doc = (getattr(pg, "numero_documento", None) or "").strip()
        refp = (getattr(pg, "referencia_pago", None) or "").strip()
        referencia_tabla = (doc or refp or f"Pago #{pago_id}")[:32]
        cedula_comprobante = (getattr(pg, "cedula_cliente", None) or "").strip() or "-"
        aplicacion_cuotas = desglose_aplicacion_cuotas_por_pago(db, pago_id)
        resultado.append(
            {
                "pago_id": pago_id,
                "prestamo_id": int(prestamo_id) if prestamo_id is not None else None,
                "banco": banco,
                "fecha_pago_display": _fmt_fecha_hora_pago_estado_cuenta(fp),
                "fecha_registro_display": _fmt_fecha_hora_pago_estado_cuenta(fr),
                "monto_display": monto_display,
                "tasa_display": tasa_display,
                "subtotal_usd": monto_usd,
                "es_bs": es_bs,
                "recibo_prestamo_id": rp,
                "recibo_cuota_id": rc,
                "referencia_tabla": referencia_tabla,
                "numero_documento": doc or None,
                "referencia_pago": refp or None,
                "cedula_comprobante": cedula_comprobante,
                "aplicacion_cuotas": aplicacion_cuotas,
            }
        )"""
if old_append not in t:
    raise SystemExit("listar append block not found")
t = t.replace(old_append, new_append, 1)
p.write_text(t, encoding="utf-8")
print("ok", p)
