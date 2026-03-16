# Patch sync_from_db to decrypt version 2 cuentas
import os
path = os.path.join(os.path.dirname(__file__), "..", "app", "core", "email_config_holder.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

old = """                if isinstance(data, dict):
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

new = """                if isinstance(data, dict):
                    decrypted_data = data.copy()
                    if decrypted_data.get("version") == 2 and "cuentas" in decrypted_data:
                        for i, cuenta in enumerate(decrypted_data["cuentas"]):
                            if not isinstance(cuenta, dict):
                                continue
                            decrypted_data["cuentas"][i] = dict(cuenta)
                            for field in SENSITIVE_FIELDS:
                                enc_key = f"{field}_encriptado"
                                if enc_key in cuenta and cuenta[enc_key]:
                                    raw = cuenta[enc_key]
                                    enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                                    decrypted = _decrypt_value_safe(enc_bytes)
                                    if decrypted:
                                        decrypted_data["cuentas"][i][field] = decrypted
                    else:
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

if old in c:
    c = c.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("sync_from_db v2 decrypt patched")
else:
    print("Block not found - sync_from_db already patched or different")
