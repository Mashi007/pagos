from pathlib import Path

# 1) pagos.py: normalize PagoConError.numero_documento on bulk error save
P = Path("c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/pagos.py")
s = P.read_text(encoding="utf-8")
old = "                    numero_documento=pce_data[\"numero_doc\"],\n"
new = "                    numero_documento=normalize_documento(pce_data.get(\"numero_doc\")),\n"
if old not in s:
    raise SystemExit("pagos.py PagoConError line not found")
s = s.replace(old, new, 1)
P.write_text(s, encoding="utf-8")

# 2) pagos_con_errores.py
P2 = Path("c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/pagos_con_errores.py")
t = P2.read_text(encoding="utf-8")
if "from app.core.documento import normalize_documento" not in t:
    ins = "from app.core.database import get_db\n"
    if ins not in t:
        raise SystemExit("pagos_con_errores anchor not found")
    t = t.replace(
        ins,
        ins + "from app.core.documento import normalize_documento\n"
        "from app.services.pago_numero_documento import numero_documento_ya_registrado\n",
        1,
    )

old_c = """    ref = (payload.numero_documento or "").strip() or "N/A"
    row = PagoConError(
        cedula_cliente=payload.cedula_cliente.strip(),
        prestamo_id=payload.prestamo_id,
        fecha_pago=fecha_ts,
        monto_pagado=payload.monto_pagado,
        numero_documento=(payload.numero_documento or "").strip() or None,
"""
new_c = """    num_norm = normalize_documento(payload.numero_documento)
    if num_norm and numero_documento_ya_registrado(db, num_norm):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un pago o registro en revisión con ese número de documento.",
        )
    ref = (num_norm or (payload.numero_documento or "").strip() or "N/A")[:100]
    row = PagoConError(
        cedula_cliente=payload.cedula_cliente.strip(),
        prestamo_id=payload.prestamo_id,
        fecha_pago=fecha_ts,
        monto_pagado=payload.monto_pagado,
        numero_documento=num_norm,
"""
if old_c not in t:
    raise SystemExit("crear_pago_con_error block not found")
t = t.replace(old_c, new_c, 1)

old_b = """            ref = (payload.numero_documento or "").strip() or "N/A"
            row = PagoConError(
                cedula_cliente=(payload.cedula_cliente or "").strip(),
                prestamo_id=payload.prestamo_id,
                fecha_pago=fecha_ts,
                monto_pagado=payload.monto_pagado,
                numero_documento=(payload.numero_documento or "").strip() or None,
"""
new_b = """            num_norm = normalize_documento(payload.numero_documento)
            if num_norm and numero_documento_ya_registrado(db, num_norm):
                results.append(
                    {
                        "success": False,
                        "error": "Ya existe un pago o registro en revisión con ese número de documento.",
                        "payload_index": len(results),
                    }
                )
                continue
            ref = (num_norm or (payload.numero_documento or "").strip() or "N/A")[:100]
            row = PagoConError(
                cedula_cliente=(payload.cedula_cliente or "").strip(),
                prestamo_id=payload.prestamo_id,
                fecha_pago=fecha_ts,
                monto_pagado=payload.monto_pagado,
                numero_documento=num_norm,
"""
if old_b not in t:
    raise SystemExit("batch crear_pago_con_error block not found")
t = t.replace(old_b, new_b, 1)

P2.write_text(t, encoding="utf-8")
print("pce endpoints patched")
