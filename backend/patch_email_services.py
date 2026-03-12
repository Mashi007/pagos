# Add per-service email on/off: stub keys and EmailConfigUpdate fields
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 1) configuracion_email.py - stub
path1 = "app/api/v1/endpoints/configuracion_email.py"
with open(path1, "r", encoding="utf-8") as f:
    t = f.read()
t = t.replace(
    '    "email_activo": "true",\n    "imap_host": "",',
    '''    "email_activo": "true",
    "email_activo_notificaciones": "true",
    "email_activo_informe_pagos": "true",
    "email_activo_estado_cuenta": "true",
    "email_activo_cobros": "true",
    "email_activo_campanas": "true",
    "email_activo_tickets": "true",
    "imap_host": "",'''
)
t = t.replace(
    "    email_activo: Optional[str] = None\n    imap_host: Optional[str] = None",
    """    email_activo: Optional[str] = None
    email_activo_notificaciones: Optional[str] = None
    email_activo_informe_pagos: Optional[str] = None
    email_activo_estado_cuenta: Optional[str] = None
    email_activo_cobros: Optional[str] = None
    email_activo_campanas: Optional[str] = None
    email_activo_tickets: Optional[str] = None
    imap_host: Optional[str] = None"""
)
with open(path1, "w", encoding="utf-8") as f:
    f.write(t)
print("configuracion_email.py OK")

# 2) email_config_holder.py - update_from_api keys + get_email_activo + get_email_activo_servicio
path2 = "app/core/email_config_holder.py"
with open(path2, "r", encoding="utf-8") as f:
    t = f.read()

# update_from_api: add email_activo and email_activo_*
t = t.replace(
    '    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "tickets_notify_emails", "modo_pruebas", "email_pruebas", "emails_pruebas", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl"):',
    '    for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "tickets_notify_emails", "modo_pruebas", "email_pruebas", "emails_pruebas", "email_activo", "email_activo_notificaciones", "email_activo_informe_pagos", "email_activo_estado_cuenta", "email_activo_cobros", "email_activo_campanas", "email_activo_tickets", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl"):'
)

# After get_tickets_notify_emails, add get_email_activo and get_email_activo_servicio
old_block = '''def get_tickets_notify_emails() -> List[str]:
    """Lista de emails a los que notificar cuando se crea/actualiza un ticket (contactos prestablecidos)."""
    raw = _current.get("tickets_notify_emails") or getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


def update_from_api'''

new_block = '''def get_tickets_notify_emails() -> List[str]:
    """Lista de emails a los que notificar cuando se crea/actualiza un ticket (contactos prestablecidos)."""
    raw = _current.get("tickets_notify_emails") or getattr(settings, "TICKETS_NOTIFY_EMAIL", None) or ""
    return [e.strip() for e in raw.split(",") if e.strip()]


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
    key = f"email_activo_{servicio}"
    if key not in _current or _current[key] is None:
        return True  # por defecto activo
    v = _current[key]
    return (str(v).lower() == "true" or v is True)


def update_from_api'''

if new_block not in t or old_block not in t:
    raise SystemExit("holder: block not found")
t = t.replace(old_block, new_block)
with open(path2, "w", encoding="utf-8") as f:
    f.write(t)
print("email_config_holder.py OK")
