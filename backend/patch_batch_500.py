# Script to patch pagos batch endpoint: safe cedula handling and case-insensitive client lookup
path = "app/api/v1/endpoints/pagos.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Safe cedula in set comprehension
old1 = "cedulas_con_prestamo = list({p.cedula_cliente.strip().upper() for p in pagos_list if p.cedula_cliente and p.prestamo_id})"
new1 = "cedulas_con_prestamo = list({(p.cedula_cliente or \"\").strip().upper() for p in pagos_list if (p.cedula_cliente or \"\").strip() and p.prestamo_id})"
content = content.replace(old1, new1)

# 2) Case-insensitive client lookup (func.upper already imported via select/func)
old2 = "ced_rows = db.execute(select(Cliente.cedula).where(Cliente.cedula.in_(cedulas_con_prestamo))).scalars().all()"
new2 = "ced_rows = db.execute(select(Cliente.cedula).where(func.upper(Cliente.cedula).in_(cedulas_con_prestamo))).scalars().all()"
content = content.replace(old2, new2)

# 3) Normalize valid_cedulas to uppercase for comparison
old3 = "valid_cedulas = {r[0] for r in ced_rows}"
new3 = "valid_cedulas = {(r[0] or \"\").strip().upper() for r in ced_rows}"
content = content.replace(old3, new3)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Batch endpoint patched.")
