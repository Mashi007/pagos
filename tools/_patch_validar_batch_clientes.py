# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\pagos.py")
t = p.read_text(encoding="utf-8")

old = (
    "    - Cédulas: deben existir en tabla préstamos (al menos un crédito con esa cédula normalizada).\n"
)
new = (
    "    - Cédulas: deben existir en tabla clientes (misma clave que FK fk_pagos_cedula al guardar pagos).\n"
)
if old in t:
    t = t.replace(old, new, 1)
else:
    # fallback: ascii doc
    t = t.replace(
        "    - Cédulas: deben existir en tabla préstamos (al menos un crédito con esa cédula normalizada).\n",
        "    - Cédulas: deben existir en tabla clientes (FK al guardar pagos).\n",
        1,
    )

old_block = """    if cedulas_norm:

        pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

        rows = db.execute(select(pc).where(pc.in_(cedulas_norm)).distinct()).all()

        cedulas_existentes = {r[0] for r in rows if r and r[0]}"""

new_block = """    if cedulas_norm:

        cc = func.upper(func.replace(Cliente.cedula, "-", ""))

        rows = db.execute(select(cc).where(cc.in_(cedulas_norm)).distinct()).all()

        cedulas_existentes = {r[0] for r in rows if r and r[0]}"""

if old_block not in t:
    raise SystemExit("prestamo cedula block not found")
t = t.replace(old_block, new_block, 1)

p.write_text(t, encoding="utf-8", newline="\n")
print("OK validar_filas_batch -> clientes")
