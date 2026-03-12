# Patch _load_email_config_from_db to handle *_encriptado keys (not in stub)
path = "backend/app/api/v1/endpoints/configuracion_email.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old = """                for k, v in data.items():
                    if k in _email_config_stub and v is not None:
                        if k.endswith("_encriptado"):
                            base_field = k.replace("_encriptado", "")
                            if base_field in SENSITIVE_FIELDS:
                                try:
                                    encrypted_bytes = bytes.fromhex(v) if isinstance(v, str) else v
                                    decrypted = _decrypt_value_safe(encrypted_bytes)
                                    if decrypted:
                                        _email_config_stub[base_field] = decrypted
                                        continue
                                except Exception:
                                    pass
                        _email_config_stub[k] = v"""

new = """                for k, v in data.items():
                    if k.endswith("_encriptado") and v is not None:
                        base_field = k.replace("_encriptado", "")
                        if base_field in _email_config_stub and base_field in SENSITIVE_FIELDS:
                            try:
                                encrypted_bytes = bytes.fromhex(v) if isinstance(v, str) else v
                                decrypted = _decrypt_value_safe(encrypted_bytes)
                                if decrypted:
                                    _email_config_stub[base_field] = decrypted
                            except Exception:
                                pass
                        continue
                    if k in _email_config_stub and v is not None:
                        _email_config_stub[k] = v"""

if old not in text:
    raise SystemExit("Old block not found")
text = text.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Patched OK")
