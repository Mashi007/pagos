# Eliminar salvedad Z999999999: cédula única para todos los valores
path = "app/api/v1/endpoints/clientes.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) create_cliente: quitar "if cedula_norm != Z999999999" y aplicar siempre el chequeo
old1 = """    # Prohibir duplicado por cédula (Z999999999 puede repetirse: clientes sin cédula)
    if cedula_norm != "Z999999999":
        existing_cedula = db.execute(
            select(Cliente.id).where(Cliente.cedula == cedula_norm)
        ).first()
        if existing_cedula:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con la misma cédula. Cliente existente ID: {existing_cedula[0]}",
            )"""

new1 = """    # Prohibir duplicado por cédula (única para todos los valores)
    existing_cedula = db.execute(
        select(Cliente.id).where(Cliente.cedula == cedula_norm)
    ).first()
    if existing_cedula:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un cliente con la misma cédula. Cliente existente ID: {existing_cedula[0]}",
        )"""

# 2) check_cedulas: quitar filtro de Z999999999
old2 = """    cedulas_norm = [c for c in cedulas_norm if c != "Z999999999"]
    if not cedulas_norm:
        return CheckCedulasResponse(existing_cedulas=[])"""

new2 = ""

# 3) update: quitar comentario y condición "!= Z999999999"
old3 = """    # Validar duplicados: no permitir cédula, nombre, email ni teléfono igual a otro cliente
    # Z999999999 puede repetirse (clientes sin cédula)
    if "cedula" in data:
        cedula_norm = (_normalize_for_duplicate(data.get("cedula") or getattr(row, "cedula") or "") or "Z999999999").upper()  # Uppercase para consistency
        data["cedula"] = cedula_norm
        if cedula_norm and cedula_norm != "Z999999999":
            existing = db.execute(
                select(Cliente.id).where(Cliente.cedula == cedula_norm, Cliente.id != cliente_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe otro cliente con la misma cédula. Cliente existente ID: {existing[0]}",
                )"""

new3 = """    # Validar duplicados: no permitir cédula, nombre, email ni teléfono igual a otro cliente
    if "cedula" in data:
        cedula_norm = (_normalize_for_duplicate(data.get("cedula") or getattr(row, "cedula") or "") or "Z999999999").upper()
        data["cedula"] = cedula_norm
        if cedula_norm:
            existing = db.execute(
                select(Cliente.id).where(Cliente.cedula == cedula_norm, Cliente.id != cliente_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe otro cliente con la misma cédula. Cliente existente ID: {existing[0]}",
                )"""

n = 0
if old1 in content:
    content = content.replace(old1, new1)
    n += 1
if old2 in content:
    content = content.replace(old2, new2)
    n += 1
if old3 in content:
    content = content.replace(old3, new3)
    n += 1

# Try with common encoding variants (comment with ó vs o)
old1_alt = old1.replace("cédula", "cedula").replace("cédula", "cedula")
if old1_alt != old1 and old1_alt in content and old1 not in content:
    content = content.replace(old1_alt, new1.replace("cédula", "cedula"))
    n += 1

if n > 0 or old1 in content or old2 in content or old3 in content:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched:", n, "replacements")
else:
    # Try line-by-line / smaller chunks
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "Z999999999 puede repetirse" in line or "puede repetirse" in line and "cedula" in line.lower():
            i += 1
            continue
        if "cedulas_norm = [c for c in cedulas_norm if c != \"Z999999999\"]" in line:
            i += 1
            if i < len(lines) and "if not cedulas_norm:" in lines[i]:
                i += 1
            if i < len(lines) and "return CheckCedulasResponse" in lines[i]:
                i += 1
            continue
        if "if cedula_norm != \"Z999999999\":" in line:
            # unindent next block
            i += 1
            while i < len(lines) and (lines[i].startswith("        ") or lines[i].strip() == ""):
                out.append(lines[i].replace("        ", "    ", 1) if lines[i].startswith("        ") else lines[i])
                i += 1
            continue
        if "if cedula_norm and cedula_norm != \"Z999999999\":" in line:
            out.append(line.replace("if cedula_norm and cedula_norm != \"Z999999999\":", "if cedula_norm:"))
            i += 1
            continue
        out.append(line)
        i += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Patched (line mode)")
