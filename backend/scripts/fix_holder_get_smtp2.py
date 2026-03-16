# Fix get_smtp_config using regex (docstring encoding may vary)
import os
import re
path = os.path.join(os.path.dirname(__file__), "..", "app", "core", "email_config_holder.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

new = '''def get_smtp_config(servicio: Optional[str] = None, tipo_tab: Optional[str] = None) -> dict[str, Any]:
    """Devuelve la config SMTP para el servicio/tab. Cobros=cuenta 1, Estado cuenta=2, Notificaciones=cuenta por tab (3 o 4)."""
    sync_from_db()
    if servicio and _cuentas_data.get("cuentas"):
        asignacion = _cuentas_data.get("asignacion") or {}
        idx = obtener_indice_cuenta(servicio, tipo_tab, asignacion)
        idx = max(1, min(idx, NUM_CUENTAS))
        cu = _cuentas_data["cuentas"][idx - 1]
        if isinstance(cu, dict) and (cu.get("smtp_user") or "").strip():
            return {
                "smtp_host": cu.get("smtp_host") or "",
                "smtp_port": int(cu.get("smtp_port") or 587),
                "smtp_user": cu.get("smtp_user") or "",
                "smtp_password": cu.get("smtp_password") or "",
                "from_email": cu.get("from_email") or cu.get("smtp_user") or "",
                "from_name": cu.get("from_name") or "RapiCredit",
                "smtp_use_tls": cu.get("smtp_use_tls", "true"),
            }
    if _current.get("smtp_user"):'''

pat = re.compile(
    r'def get_smtp_config\(\) -> dict\[str, Any\]:\s*\n\s*"""[^"]*"""\s*\n\s*sync_from_db\(\)\s*\n\s*if _current\.get\("smtp_user"\):',
    re.DOTALL
)
m = pat.search(c)
if m:
    c = c[:m.start()] + new + c[m.end():]
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("get_smtp_config patched")
else:
    # try shorter pattern
    if "def get_smtp_config() ->" in c and "obtener_indice_cuenta" not in c:
        print("Pattern not found; file content around get_smtp_config:")
        i = c.find("def get_smtp_config()")
        print(repr(c[i:i+280]))
    else:
        print("Already patched or pattern mismatch")
