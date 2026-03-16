path = "backend/app/api/v1/endpoints/configuracion_email_cuentas.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
old = '"tickets_notify_emails": payload.tickets_notify_emails or "",\n    }\n    update_from_api({'
new = '"tickets_notify_emails": payload.tickets_notify_emails or "",\n        "modo_pruebas_cobros": payload.modo_pruebas or "true",\n        "modo_pruebas_estado_cuenta": payload.modo_pruebas or "true",\n    }\n    update_from_api({'
if old in c:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("OK")
else:
    print("Not found")
    idx = c.find("tickets_notify_emails")
    print(repr(c[idx : idx + 130]))
