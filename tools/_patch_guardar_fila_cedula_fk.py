# -*- coding: utf-8 -*-
"""Asegura cedula en guardar_fila_editable = clientes.cedula (FK fk_pagos_cedula)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
t = p.read_text(encoding="utf-8")

old_imp = "from app.utils.cedula_almacenamiento import alinear_cedulas_clientes_existentes"
new_imp = (
    "from app.utils.cedula_almacenamiento import "
    "alinear_cedulas_clientes_existentes, normalizar_cedula_almacenamiento"
)
if old_imp not in t or new_imp in t:
    if new_imp not in t:
        raise SystemExit("import line not found or already patched wrong")
else:
    t = t.replace(old_imp, new_imp, 1)

marker = (
    '                detail="La cédula no tiene préstamo asociado; registre el crédito antes de cargar el pago.",\n'
    "\n"
    "            )\n"
    "\n"
    "\n"
    "\n"
    "        # Crear pago\n"
)
insert = (
    '                detail="La cédula no tiene préstamo asociado; registre el crédito antes de cargar el pago.",\n'
    "\n"
    "            )\n"
    "\n"
    "\n"
    "\n"
    "        # Cedula en pagos debe existir en clientes (FK fk_pagos_cedula): usar la del cliente del prestamo.\n"
    "        prest = db.get(Prestamo, prestamo_id)\n"
    "        if not prest:\n"
    '            raise HTTPException(status_code=404, detail="Prestamo no encontrado")\n'
    "        cli = db.get(Cliente, prest.cliente_id)\n"
    "        if not cli:\n"
    "            raise HTTPException(\n"
    "                status_code=400,\n"
    '                detail="El prestamo no tiene cliente asociado en BD; no se puede registrar el pago.",\n'
    "            )\n"
    "        cedula_fk = normalizar_cedula_almacenamiento(cli.cedula) or normalizar_cedula_almacenamiento(\n"
    "            prest.cedula\n"
    "        )\n"
    "        if not cedula_fk:\n"
    '            raise HTTPException(status_code=400, detail="Cedula del cliente no disponible en BD.")\n'
    "        cedula_input = normalizar_cedula_almacenamiento(cedula.strip())\n"
    "        if cedula_input and cedula_input != cedula_fk:\n"
    "            raise HTTPException(\n"
    "                status_code=400,\n"
    '                detail=f"La cedula no coincide con la del cliente del prestamo (en BD: {cedula_fk}).",\n'
    "            )\n"
    "\n"
    "\n"
    "\n"
    "        # Crear pago\n"
)

if marker not in t:
    raise SystemExit("marker block not found (encoding?)")
t = t.replace(marker, insert, 1)

old_pago = (
    "            cedula_cliente=cedula.strip().upper() if cedula else \"\",  # Normalize to uppercase\n"
)
new_pago = "            cedula_cliente=cedula_fk,\n"
if old_pago not in t:
    raise SystemExit("Pago cedula_cliente line not found")
t = t.replace(old_pago, new_pago, 1)

p.write_text(t, encoding="utf-8", newline="\n")
print("OK", p)
