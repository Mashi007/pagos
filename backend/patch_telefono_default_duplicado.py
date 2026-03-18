# Permitir duplicado solo para telefono por defecto +584111111111 (digits 4111111111)
path = "app/api/v1/endpoints/clientes.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Constante: digitos del telefono por defecto (unico valor que se admite duplicado)
TEL_DEFAULT_DIGITS = "4111111111"

# create_cliente: no reemplazar por +589999999999 cuando el telefono es el por defecto
old_create = """    # Si teléfono duplicado (2 números exactamente iguales) → reemplazar por +589999999999
    telefono_final = payload.telefono
    if len(telefono_dig) >= 8:
        rows_telefono = db.execute("""

new_create = """    # Si teléfono duplicado (2 números exactamente iguales) → reemplazar por +589999999999
    # Excepción: +584111111111 es valor por defecto y es el único que se admite duplicado
    telefono_final = payload.telefono
    tel_10 = telefono_dig[-10:] if len(telefono_dig) >= 10 else telefono_dig
    if len(telefono_dig) >= 8 and tel_10 != "4111111111":
        rows_telefono = db.execute("""

# update: no reemplazar por +589999999999 cuando el telefono es el por defecto
old_update = """    if "telefono" in data:
        telefono_dig = _digits_telefono(data.get("telefono") or getattr(row, "telefono") or "")
        if len(telefono_dig) >= 8:
            rows_telefono = db.execute("""

new_update = """    if "telefono" in data:
        telefono_dig = _digits_telefono(data.get("telefono") or getattr(row, "telefono") or "")
        tel_10 = telefono_dig[-10:] if len(telefono_dig) >= 10 else telefono_dig
        if len(telefono_dig) >= 8 and tel_10 != "4111111111":
            rows_telefono = db.execute("""

n = 0
if old_create in content:
    content = content.replace(old_create, new_create)
    n += 1
if old_update in content:
    content = content.replace(old_update, new_update)
    n += 1

if n == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Backend patched OK")
else:
    print("Only", n, "replacements (expected 2)")
