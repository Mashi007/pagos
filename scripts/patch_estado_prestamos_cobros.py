# python scripts/patch_estado_prestamos_cobros.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- prestamos get_cuotas ---
pp = ROOT / "backend/app/api/v1/endpoints/prestamos.py"
t = pp.read_text(encoding="utf-8")
old_imp = "from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo\n"
if "pagos_cuotas_sincronizacion" not in t:
    t = t.replace(old_imp, old_imp + "from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos\n", 1)
old_block = """    n_aplicados = aplicar_pagos_pendientes_prestamo(prestamo_id, db)
    if n_aplicados > 0:
        db.commit()
        logger.info("get_cuotas_prestamo: aplicados %s pago(s) pendientes al pr\u00e9stamo %s", n_aplicados, prestamo_id)"""
# try ascii prestamo
old_block2 = old_block.replace("pr\u00e9stamo", "préstamo")
candidates = [
    """    n_aplicados = aplicar_pagos_pendientes_prestamo(prestamo_id, db)
    if n_aplicados > 0:
        db.commit()
        logger.info("get_cuotas_prestamo: aplicados %s pago(s) pendientes al préstamo %s", n_aplicados, prestamo_id)""",
    old_block2,
]
new_block = """    n_aplicados = sincronizar_pagos_pendientes_a_prestamos(db, [prestamo_id])
    if n_aplicados > 0:
        logger.info("get_cuotas_prestamo: aplicados %s pago(s) pendientes al préstamo %s", n_aplicados, prestamo_id)"""
replaced = False
for c in candidates:
    if c in t:
        t = t.replace(c, new_block, 1)
        replaced = True
        break
if not replaced:
    # fuzzy: single line replace
    import re
    m = re.search(
        r"    n_aplicados = aplicar_pagos_pendientes_prestamo\(prestamo_id, db\)\s*\n"
        r"    if n_aplicados > 0:\s*\n"
        r"        db\.commit\(\)\s*\n"
        r'        logger\.info\("get_cuotas_prestamo: aplicados %s pago\(s\) pendientes al .+?", n_aplicados, prestamo_id\)',
        t,
    )
    if not m:
        raise SystemExit("prestamos get_cuotas block not found")
    t = t[: m.start()] + new_block + t[m.end() :]
pp.write_text(t, encoding="utf-8")
print("patched prestamos.py")

# --- cobros list filter ---
cp = ROOT / "backend/app/api/v1/endpoints/cobros.py"
ct = cp.read_text(encoding="utf-8")
old_f = '        q = q.where(PagoReportado.estado != "aprobado")\n        count_q = count_q.where(PagoReportado.estado != "aprobado")'
new_f = "        q = q.where(~PagoReportado.estado.in_((\"aprobado\", \"importado\")))\n        count_q = count_q.where(~PagoReportado.estado.in_((\"aprobado\", \"importado\")))"
if old_f in ct:
    ct = ct.replace(old_f, new_f, 1)
    cp.write_text(ct, encoding="utf-8")
    print("patched cobros.py filter")
else:
    print("cobros filter pattern not found, skip")

# --- estado_cuenta_publico ---
ep = ROOT / "backend/app/api/v1/endpoints/estado_cuenta_publico.py"
et = ep.read_text(encoding="utf-8")
et = et.replace(
    "from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo\n",
    "from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos\n",
    1,
)
# remove _sincronizar function block
start = et.find("def _sincronizar_pagos_a_cuotas_prestamos(")
if start >= 0:
    end = et.find("\n\n\ndef _obtener_recibos_cliente", start)
    if end < 0:
        end = et.find("\ndef _obtener_recibos_cliente", start)
    if end < 0:
        raise SystemExit("could not find end of _sincronizar")
    et = et[:start] + et[end + 2 :]  # keep one newline before def _obtener
    print("removed _sincronizar from estado_cuenta")
et = et.replace("_sincronizar_pagos_a_cuotas_prestamos(db, prestamo_ids)", "sincronizar_pagos_pendientes_a_prestamos(db, prestamo_ids)")
et = et.replace("\n    import base64\n    pdf_b64 = base64.b64encode", "\n    pdf_b64 = base64.b64encode")
ep.write_text(et, encoding="utf-8")
print("patched estado_cuenta_publico.py")

print("done")
