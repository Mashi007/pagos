import os
path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "configuracion_email.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

if "{{LOGO_URL}}" in c and "logo_url" in c and "body.replace" in c:
    print("Already patched")
    raise SystemExit(0)

old = """    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    recipients = [destino]"""

new = """    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    if "{{LOGO_URL}}" in body:
        try:
            from app.core.email import _logo_url_for_email
            body = body.replace("{{LOGO_URL}}", _logo_url_for_email())
        except Exception:
            body = body.replace("{{LOGO_URL}}", "https://rapicredit.onrender.com/pagos/logos/rapicredit-public.png")
    recipients = [destino]"""

if old not in c:
    print("Pattern not found")
    raise SystemExit(1)
c = c.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched configuracion_email.py: {{LOGO_URL}} replaced in prueba body")
