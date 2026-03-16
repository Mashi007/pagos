# Fix get_smtp_config and sync_from_db in email_config_holder
import os
path = os.path.join(os.path.dirname(__file__), "..", "app", "core", "email_config_holder.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Fix get_smtp_config
old = """def get_smtp_config() -> dict[str, Any]:
    \"\"\"Devuelve la config SMTP actual. Siempre carga desde BD primero para usar el correo guardado en Configuraci\u00f3n > Email (no el de .env).\"\"\"
    sync_from_db()
    if _current.get("smtp_user"):"""

new = """def get_smtp_config(servicio: Optional[str] = None, tipo_tab: Optional[str] = None) -> dict[str, Any]:
    \"\"\"Devuelve la config SMTP para el servicio/tab. Cobros=cuenta 1, Estado cuenta=2, Notificaciones=cuenta por tab (3 o 4).\"\"\"
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
    if _current.get("smtp_user"):"""

if old in c:
    c = c.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("get_smtp_config patched")
else:
    print("get_smtp_config block not found (maybe already patched)")
