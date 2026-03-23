# -*- coding: utf-8 -*-
"""Cedula clientes: comparacion sin distincion de mayusculas + alinear legacy a mayusculas antes de FK pagos."""
from pathlib import Path

p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\pagos.py")
t = p.read_text(encoding="utf-8")

old_early = """        cedula_norm_in = normalizar_cedula_almacenamiento(cedula)
        if not cedula_norm_in:
            raise HTTPException(status_code=400, detail="Cédula requerida")
        cli_por_cedula = db.execute(
            select(Cliente.id).where(Cliente.cedula == cedula_norm_in).limit(1)
        ).first()
        if not cli_por_cedula:
            raise HTTPException(
                status_code=400,
                detail="La cédula no está registrada en clientes. No se puede guardar el pago.",
            )"""

new_early = """        cedula_norm_in = normalizar_cedula_almacenamiento(cedula)
        if not cedula_norm_in:
            raise HTTPException(status_code=400, detail="Cédula requerida")
        cn_in = cedula_norm_in.replace("-", "").upper()
        cc_cli = func.upper(func.replace(Cliente.cedula, "-", ""))
        cli_por_cedula = db.execute(
            select(Cliente.id).where(cc_cli == cn_in).limit(1)
        ).first()
        if not cli_por_cedula:
            raise HTTPException(
                status_code=400,
                detail="La cédula no está registrada en clientes. No se puede guardar el pago.",
            )"""

if old_early not in t:
    raise SystemExit("early block not found (encoding?)")

t = t.replace(old_early, new_early, 1)

old_align = """        cli = db.get(Cliente, prest.cliente_id)
        if not cli:
            raise HTTPException(
                status_code=400,
                detail="El prestamo no tiene cliente asociado en BD; no se puede registrar el pago.",
            )
        cedula_fk = normalizar_cedula_almacenamiento(cli.cedula) or normalizar_cedula_almacenamiento(
            prest.cedula
        )
        if not cedula_fk:
            raise HTTPException(status_code=400, detail="Cedula del cliente no disponible en BD.")
        cedula_input = normalizar_cedula_almacenamiento(cedula.strip())
        if cedula_input and cedula_input != cedula_fk:
            raise HTTPException(
                status_code=400,
                detail=f"La cedula no coincide con la del cliente del prestamo (en BD: {cedula_fk}).",
            )"""

new_align = """        cli = db.get(Cliente, prest.cliente_id)
        if not cli:
            raise HTTPException(
                status_code=400,
                detail="El prestamo no tiene cliente asociado en BD; no se puede registrar el pago.",
            )
        # Datos legacy: clientes.cedula en minusculas; FK pagos.cedula debe coincidir con clientes.cedula
        ced_norm_cli = normalizar_cedula_almacenamiento(cli.cedula)
        if ced_norm_cli and ced_norm_cli != (cli.cedula or ""):
            cli.cedula = ced_norm_cli
            db.flush()
        cedula_fk = normalizar_cedula_almacenamiento(cli.cedula) or normalizar_cedula_almacenamiento(
            prest.cedula
        )
        if not cedula_fk:
            raise HTTPException(status_code=400, detail="Cedula del cliente no disponible en BD.")
        cedula_input = normalizar_cedula_almacenamiento(cedula.strip())
        cn_body = (cedula_input or "").replace("-", "").upper()
        cn_fk = (cedula_fk or "").replace("-", "").upper()
        if cedula_input and cn_body != cn_fk:
            raise HTTPException(
                status_code=400,
                detail=f"La cedula no coincide con la del cliente del prestamo (en BD: {cedula_fk}).",
            )"""

if old_align not in t:
    raise SystemExit("align block not found")

t = t.replace(old_align, new_align, 1)

p.write_text(t, encoding="utf-8", newline="\n")
print("OK")
