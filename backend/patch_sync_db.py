# One-off patch for email_config_holder sync_from_db
p = "app/core/email_config_holder.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

old = """                    # Desencriptar campos sensibles si es necesario
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        if field in decrypted_data and decrypted_data[field]:
                            # Si está encriptado, desencriptar; si no, dejar como está
                            decrypted = _decrypt_value_safe(decrypted_data[field])
                            if decrypted:
                                decrypted_data[field] = decrypted
                    update_from_api(decrypted_data)"""

new = """                    # Desencriptar campos sensibles: primero _encriptado; si falla (ej. sin ENCRYPTION_KEY), usar valor en claro
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        enc_key = f"{field}_encriptado"
                        if enc_key in data and data[enc_key]:
                            raw = data[enc_key]
                            enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                            decrypted = _decrypt_value_safe(enc_bytes)
                            decrypted_data[field] = decrypted if decrypted else data.get(field)
                        elif field in data and data[field] is not None:
                            decrypted_data[field] = data[field]
                    update_from_api(decrypted_data)"""

# Normalize possible encoding in "está"
import re
old_re = re.compile(
    r"# Desencriptar campos sensibles si es necesario\s+decrypted_data = data\.copy\(\)\s+for field in SENSITIVE_FIELDS:\s+if field in decrypted_data and decrypted_data\[field\]:\s+# Si .*? desencriptar.*?\s+decrypted = _decrypt_value_safe\(decrypted_data\[field\]\)\s+if decrypted:\s+decrypted_data\[field\] = decrypted\s+update_from_api\(decrypted_data\)",
    re.DOTALL
)
if old_re.search(c):
    c = old_re.sub(
        """# Desencriptar campos sensibles: primero _encriptado; si falla (ej. sin ENCRYPTION_KEY), usar valor en claro
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        enc_key = f"{field}_encriptado"
                        if enc_key in data and data[enc_key]:
                            raw = data[enc_key]
                            enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                            decrypted = _decrypt_value_safe(enc_bytes)
                            decrypted_data[field] = decrypted if decrypted else data.get(field)
                        elif field in data and data[field] is not None:
                            decrypted_data[field] = data[field]
                    update_from_api(decrypted_data)""",
        c,
        count=1,
    )
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched sync_from_db")
elif old in c:
    c = c.replace(old, new)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched sync_from_db (exact)")
else:
    print("Block not found")
    idx = c.find("Desencriptar campos sensibles")
    if idx >= 0:
        print("Context:", repr(c[idx:idx+400]))
