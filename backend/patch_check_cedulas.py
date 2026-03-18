# One-off script to replace check_cedulas loop with single query
path = "app/api/v1/endpoints/clientes.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    seen: set[str] = set()
    existing: list[str] = []
    for ced in cedulas_norm:
        if ced in seen or ced == "Z999999999":
            continue
        seen.add(ced)
        row = db.execute(select(Cliente.cedula).where(Cliente.cedula == ced)).first()
        if row:
            existing.append(ced)
    return CheckCedulasResponse(existing_cedulas=existing)"""

new = """    cedulas_norm = [c for c in cedulas_norm if c != "Z999999999"]
    if not cedulas_norm:
        return CheckCedulasResponse(existing_cedulas=[])
    rows = db.execute(
        select(Cliente.cedula).where(Cliente.cedula.in_(cedulas_norm))
    ).scalars().all()
    existing = list(rows) if rows else []
    return CheckCedulasResponse(existing_cedulas=existing)"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("check_cedulas replaced OK")
else:
    print("Old block not found")
