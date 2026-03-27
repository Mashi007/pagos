from pathlib import Path
path = Path("backend/app/api/v1/endpoints/prestamos.py")
s = path.read_text(encoding="utf-8")
old = """    if est_despues == \"DESISTIMIENTO\" and est_antes != \"DESISTIMIENTO\":

        if getattr(row, \"fecha_desistimiento\", None) is None:

            row.fecha_desistimiento = hoy_negocio()

    try:"""
new = """    if est_despues == \"DESISTIMIENTO\" and est_antes != \"DESISTIMIENTO\":

        if getattr(row, \"fecha_desistimiento\", None) is None:

            row.fecha_desistimiento = hoy_negocio()

        cli_des = db.get(Cliente, row.cliente_id)

        if cli_des is not None:

            cli_des.estado = \"FINALIZADO\"

    try:"""
if old not in s:
    raise SystemExit("anchor not found")
path.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
print("ok")
