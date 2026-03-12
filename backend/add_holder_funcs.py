path = "app/core/email_config_holder.py"
with open(path, "r", encoding="utf-8") as f:
    t = f.read()
marker = 'def update_from_api(data: dict[str, Any]) -> None:'
insert = '''
# Servicios que envian email: cada uno tiene un flag email_activo_<servicio> (true/false)
EMAIL_SERVICES = ("notificaciones", "informe_pagos", "estado_cuenta", "cobros", "campanas", "tickets")

def get_email_activo() -> bool:
    """Master: si False, ningun servicio envia email."""
    sync_from_db()
    v = _current.get("email_activo") or getattr(settings, "EMAIL_ACTIVO", None) or "true"
    return (str(v).lower() == "true" or v is True)

def get_email_activo_servicio(servicio: str) -> bool:
    """True si el servicio puede enviar email (master on y flag del servicio on)."""
    if not get_email_activo():
        return False
    key = "email_activo_" + servicio
    if key not in _current or _current[key] is None:
        return True
    v = _current[key]
    return (str(v).lower() == "true" or v is True)

'''
t = t.replace(marker, insert + marker, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(t)
print("OK")
