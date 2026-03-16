# Patch send_email to pass servicio and tipo_tab to get_smtp_config
import os
import re
path = os.path.join(os.path.dirname(__file__), "..", "app", "core", "email.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Add tipo_tab parameter after servicio
c = c.replace(
    "respetar_destinos_manuales: bool = False,\n    servicio: Optional[str] = None,\n) -> Tuple[bool, Optional[str]]:",
    "respetar_destinos_manuales: bool = False,\n    servicio: Optional[str] = None,\n    tipo_tab: Optional[str] = None,\n) -> Tuple[bool, Optional[str]]:",
    1
)
# Pass servicio and tipo_tab to get_smtp_config
c = c.replace(
    "has_attachments = bool(attachments)\n    cfg = get_smtp_config()",
    "has_attachments = bool(attachments)\n    cfg = get_smtp_config(servicio=servicio, tipo_tab=tipo_tab)",
    1
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("email.py send_email patched")
