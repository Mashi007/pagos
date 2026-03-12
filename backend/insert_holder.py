# insert get_email_activo into email_config_holder (read with replace to avoid decode error)
path = "app/core/email_config_holder.py"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
out = []
done = False
for i, line in enumerate(lines):
    if not done and 'def update_from_api(data: dict[str, Any])' in line:
        out.append("\n")
        out.append("# Servicios que envian email: flag email_activo_<servicio>\n")
        out.append('EMAIL_SERVICES = ("notificaciones", "informe_pagos", "estado_cuenta", "cobros", "campanas", "tickets")\n')
        out.append("\n")
        out.append("def get_email_activo() -> bool:\n")
        out.append('    """Master: si False, ningun servicio envia email."""\n')
        out.append("    sync_from_db()\n")
        out.append('    v = _current.get("email_activo") or getattr(settings, "EMAIL_ACTIVO", None) or "true"\n')
        out.append('    return (str(v).lower() == "true" or v is True)\n')
        out.append("\n")
        out.append("def get_email_activo_servicio(servicio: str) -> bool:\n")
        out.append('    """True si el servicio puede enviar email."""\n')
        out.append("    if not get_email_activo():\n")
        out.append("        return False\n")
        out.append('    key = "email_activo_" + servicio\n')
        out.append("    if key not in _current or _current[key] is None:\n")
        out.append("        return True\n")
        out.append('    return (str(_current[key]).lower() == "true" or _current[key] is True)\n')
        out.append("\n")
        done = True
    out.append(line)
with open(path, "w", encoding="utf-8", newline="") as f:
    f.writelines(out)
print("OK")
