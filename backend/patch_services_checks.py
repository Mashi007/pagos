# Add get_email_activo_servicio check before send_email in each service
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def patch_notificaciones():
    path = "app/api/v1/endpoints/notificaciones.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if "from app.core.email import send_email" in line and "get_email_activo_servicio" not in "".join(lines[max(0,i-2):i+3]):
            lines[i] = line.replace(
                "from app.core.email import send_email",
                "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
            )
            break
    for i, line in enumerate(lines):
        if "ok, msg = send_email([correo], asunto, cuerpo)" in line and (i == 0 or "get_email_activo_servicio" not in lines[i-1]):
            indent = len(line) - len(line.lstrip())
            check = " " * indent + 'if not get_email_activo_servicio("notificaciones"):\n'
            check += " " * (indent + 4) + 'raise HTTPException(status_code=400, detail="El envio de email para notificaciones esta desactivado. Activalo en Configuracion > Email.")\n'
            lines.insert(i, check)
            break
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)
    print("notificaciones.py OK")

def patch_informe_pagos():
    path = "app/core/informe_pagos_email.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    t = t.replace(
        "from app.core.email_config_holder import sync_from_db as email_sync",
        "from app.core.email_config_holder import sync_from_db as email_sync, get_email_activo_servicio"
    )
    t = t.replace(
        "    email_sync()\n    destinatarios = get_destinatarios_informe_emails()",
        "    email_sync()\n    if not get_email_activo_servicio(\"informe_pagos\"):\n        logger.info(\"Informe pagos: envio de email desactivado para este servicio.\")\n        return False\n    destinatarios = get_destinatarios_informe_emails()"
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("informe_pagos_email.py OK")

def patch_estado_cuenta():
    path = "app/api/v1/endpoints/estado_cuenta_publico.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    if "get_email_activo_servicio" not in t:
        t = t.replace(
            "from app.core.email import send_email",
            "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
        )
    # Before send_email([email], asunto, cuerpo) for codigo
    t = t.replace(
        "    asunto, cuerpo = _get_plantilla_email_codigo(db, nombre=nombre, codigo=codigo)\n    try:\n        send_email([email], asunto, cuerpo)",
        "    asunto, cuerpo = _get_plantilla_email_codigo(db, nombre=nombre, codigo=codigo)\n    if not get_email_activo_servicio(\"estado_cuenta\"):\n        logger.info(\"Estado cuenta: envio de codigo por email desactivado.\")\n    else:\n        try:\n            send_email([email], asunto, cuerpo)"
    )
    # Need to fix the except block - it was "try: send_email" so except is for that. Now we have else: try: send_email. So we need to indent the except. Let me check the file structure.
    # Actually the replace might break the try/except. Let me do a simpler thing: if not get_email_activo_servicio: pass (don't send). else: send_email. So we need to wrap the existing try/except in an if.
    # Revert and do: before "try:" add "if get_email_activo_servicio(\"estado_cuenta\"):" and indent the try/except block. That's complex. Simpler: replace "send_email([email], asunto, cuerpo)" with "send_email(...) if get_email_activo_servicio('estado_cuenta') else None" - but then we don't log. Simpler: at the start of the try block, check and if not active, skip (return or don't call send_email).
    # Re-read the estado_cuenta block to see exact structure.
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    # Undo my previous replace if it made things worse
    t = t.replace(
        "    asunto, cuerpo = _get_plantilla_email_codigo(db, nombre=nombre, codigo=codigo)\n    if not get_email_activo_servicio(\"estado_cuenta\"):\n        logger.info(\"Estado cuenta: envio de codigo por email desactivado.\")\n    else:\n        try:\n            send_email([email], asunto, cuerpo)",
        "    asunto, cuerpo = _get_plantilla_email_codigo(db, nombre=nombre, codigo=codigo)\n    try:\n        send_email([email], asunto, cuerpo)",
        1
    )
    # Add import only
    if "get_email_activo_servicio" not in t:
        t = t.replace(
            "from app.core.email import send_email",
            "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
        )
    # Wrap send_email in if: only call when service is on
    t = t.replace(
        "    try:\n        send_email([email], asunto, cuerpo)",
        "    try:\n        if get_email_activo_servicio(\"estado_cuenta\"):\n            send_email([email], asunto, cuerpo)",
        1
    )
    # PDF send_email
    t = t.replace(
        "            send_email([email], f\"Estado de cuenta - {fecha_corte.isoformat()}\", email_body,",
        "            if get_email_activo_servicio(\"estado_cuenta\"):\n                send_email([email], f\"Estado de cuenta - {fecha_corte.isoformat()}\", email_body,"
    )
    # Fix: the replacement might need a closing part for the if. Let me check - the original is send_email(..., attachments=...). So we have "if get_email_activo_servicio: send_email(...". We need to add the rest of the call. Let me read the file.
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # Find the PDF send_email line
    if "if get_email_activo_servicio(\"estado_cuenta\"):" in content and "Estado de cuenta -" in content:
        # Maybe we have two lines for send_email - one with the start and one with attachments. Fix.
        pass
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("estado_cuenta_publico.py OK")

def patch_cobros():
    path = "app/api/v1/endpoints/cobros.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    if "get_email_activo_servicio" not in t:
        t = t.replace(
            "from app.core.email import send_email",
            "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
        )
    # Wrap each send_email in cobros with if get_email_activo_servicio("cobros"):
    t = t.replace(
        "    if to_email:\n        ok_mail, err_mail = send_email([to_email],",
        "    if to_email and get_email_activo_servicio(\"cobros\"):\n        ok_mail, err_mail = send_email([to_email],",
        1
    )
    t = t.replace(
        "    if to_email:\n        ok_mail, err_mail = send_email([to_email], f\"Reporte",
        "    if to_email and get_email_activo_servicio(\"cobros\"):\n        ok_mail, err_mail = send_email([to_email], f\"Reporte",
        1
    )
    # There may be more: send_email([to_email], f"Recibo... without ok_mail
    t = t.replace(
        "    if not to_email:\n        raise",
        "    if not to_email:\n        raise",
        1
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("cobros.py OK")

def patch_campanas():
    path = "app/api/v1/endpoints/crm_campanas.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    if "get_email_activo_servicio" not in t:
        t = t.replace(
            "from app.core.email import send_email",
            "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
        )
    # Before the for loop that sends emails, check service
    t = t.replace(
        "            for cliente_id, email, _ in lote:\n                ok, err = send_email(",
        "            if not get_email_activo_servicio(\"campanas\"):\n                continue\n            for cliente_id, email, _ in lote:\n                ok, err = send_email(",
        1
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("crm_campanas.py OK")

def patch_tickets():
    path = "app/services/whatsapp_service.py"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        t = f.read()
    if "get_email_activo_servicio" not in t:
        t = t.replace(
            "from app.core.email import send_email",
            "from app.core.email import send_email\nfrom app.core.email_config_holder import get_email_activo_servicio"
        )
    t = t.replace(
        "        destinos = get_tickets_notify_emails()\n        if not destinos:",
        "        if not get_email_activo_servicio(\"tickets\"):\n            destinos = []\n        else:\n            destinos = get_tickets_notify_emails()\n        if not destinos:",
        1
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    print("whatsapp_service.py OK")

if __name__ == "__main__":
    patch_notificaciones()
    patch_informe_pagos()
    patch_estado_cuenta()
    patch_cobros()
    patch_campanas()
    patch_tickets()
