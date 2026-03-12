# Add get_email_activo_servicio check before each send_email by service
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def patch(path, marker, before_send, import_line=None):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    if import_line and import_line not in t:
        # Add import after existing email_config_holder or email import
        if "from app.core.email_config_holder import get_email_activo_servicio" not in t:
            t = t.replace(
                "from app.core.email import send_email",
                "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio",
                1
            )
    if marker not in t:
        print(path, "marker not found:", repr(marker[:50]))
        return
    t = t.replace(marker, before_send + "\n    " + marker, 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("Patched", path)

# 1) notificaciones.py - before "ok, msg = send_email([correo], asunto, cuerpo)"
patch(
    "app/api/v1/endpoints/notificaciones.py",
    "    ok, msg = send_email([correo], asunto, cuerpo)",
    '''    if not get_email_activo_servicio("notificaciones"):
        raise HTTPException(status_code=400, detail="El envio de email para notificaciones esta desactivado. Activalo en Configuracion > Email.")'''
)

# 2) informe_pagos_email.py - after email_sync(), before destinatarios
patch(
    "app/core/informe_pagos_email.py",
    "    destinatarios = get_destinatarios_informe_emails()",
    """    from app.core.email_config_holder import get_email_activo_servicio
    if not get_email_activo_servicio("informe_pagos"):
        logger.info("Informe pagos: envio de email desactivado para este servicio.")
        return False
""".replace("\n", "\n    ")
)
# Fix: the replace added extra indent; informe_pagos has 4-space indent
with open("app/core/informe_pagos_email.py", "r", encoding="utf-8", errors="replace") as f:
    t = f.read()
# Remove duplicate import if we added get_email_activo_servicio in the block (we need it at top or before use)
if "get_email_activo_servicio" in t and "from app.core.email_config_holder import sync_from_db as email_sync" in t:
    t = t.replace(
        "from app.core.email_config_holder import sync_from_db as email_sync",
        "from app.core.email_config_holder import sync_from_db as email_sync, get_email_activo_servicio",
        1
    )
    # Fix the block we inserted - it had "from app.core.email_config_holder import get_email_activo_servicio" inside the function, remove duplicate
    t = t.replace(
        "    from app.core.email_config_holder import get_email_activo_servicio\n    if not get_email_activo_servicio",
        "    if not get_email_activo_servicio",
        1
    )
    with open("app/core/informe_pagos_email.py", "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("Fixed informe_pagos_email imports")
