# Add configuracion_email_cuentas router to configuracion.py
import os
path = os.path.join(os.path.dirname(__file__), "..", "app", "api", "v1", "endpoints", "configuracion.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

old = "from app.api.v1.endpoints import configuracion_ai, configuracion_email, configuracion_whatsapp, configuracion_informe_pagos"
new = "from app.api.v1.endpoints import configuracion_ai, configuracion_email, configuracion_email_cuentas, configuracion_whatsapp, configuracion_informe_pagos"
if "configuracion_email_cuentas" not in c:
    c = c.replace(old, new, 1)
    old2 = "router.include_router(configuracion_email.router, prefix=\"/email\", tags=[\"configuracion-email\"])"
    new2 = "router.include_router(configuracion_email.router, prefix=\"/email\", tags=[\"configuracion-email\"])\nrouter.include_router(configuracion_email_cuentas.router, prefix=\"/email\", tags=[\"configuracion-email\"])"
    c = c.replace(old2, new2, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("configuracion.py updated with cuentas router")
else:
    print("Already included")
