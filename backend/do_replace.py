path = "app/api/v1/endpoints/configuracion_email.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    try:
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload))
        db.commit()"""

new = """    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        if row and row.valor:
            try:
                data = json.loads(row.valor)
                if isinstance(data, dict) and data.get("version") == 2 and "cuentas" in data:
                    for key in _STUB_GLOBAL_KEYS:
                        if key in _email_config_stub:
                            data[key] = _email_config_stub[key]
                    row.valor = json.dumps(data)
                    db.commit()
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        payload_data = prepare_for_db_storage(_email_config_stub)
        payload = json.dumps(payload_data)
        if row:
            row.valor = payload
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload))
        db.commit()"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK")
else:
    print("OLD not found")
