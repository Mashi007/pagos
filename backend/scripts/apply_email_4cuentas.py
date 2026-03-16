"""
Script para aplicar soporte de 4 cuentas de email.
Modifica: email_config_holder.py, configuracion_email.py, email.py, notificaciones_tabs.py.
Ejecutar desde raíz del repo: python backend/scripts/apply_email_4cuentas.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "backend")
APP = os.path.join(BACKEND, "app")
CORE = os.path.join(APP, "core")
ENDPOINTS = os.path.join(APP, "api", "v1", "endpoints")


def patch_email_config_holder():
    path = os.path.join(CORE, "email_config_holder.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add import and _cuentas_data after _current
    if "_cuentas_data" in content:
        return False
    content = content.replace(
        "# Config actual: smtp_*, from_email, from_name, tickets_notify_emails (str, emails separados por coma)\n_current: dict[str, Any] = {}",
        "# Config actual: smtp_*, from_email, from_name, tickets_notify_emails (str, emails separados por coma)\n_current: dict[str, Any] = {}\n# Version 2: 4 cuentas + asignacion (cobros=1, estado_cuenta=2, notificaciones por tab=3|4)\n_cuentas_data: dict = {}",
    )
    content = content.replace(
        "from app.core.config import settings\nfrom app.core.email_phases import FASE_CONFIG_CARGA, log_phase",
        "from app.core.config import settings\nfrom app.core.email_phases import FASE_CONFIG_CARGA, log_phase\nfrom app.core.email_cuentas import migrar_config_v1_a_v2, obtener_indice_cuenta, NUM_CUENTAS",
    )

    # In sync_from_db: after parsing and decrypting, handle version 2 and set _cuentas_data
    old_sync = """                    if isinstance(data, dict):
                    decrypted_data = data.copy()
                    for field in SENSITIVE_FIELDS:
                        enc_key = f"{field}_encriptado"
                        if enc_key in data and data[enc_key]:
                            raw = data[enc_key]
                            enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                            decrypted = _decrypt_value_safe(enc_bytes)
                            decrypted_data[field] = decrypted if decrypted else data.get(field)
                        elif field in data and data[field] is not None:
                            decrypted_data[field] = data[field]
                    update_from_api(decrypted_data)"""
    new_sync = """                    if isinstance(data, dict):
                    decrypted_data = data.copy()
                    # Version 2: cuentas es lista; desencriptar cada cuenta
                    if decrypted_data.get("version") == 2 and "cuentas" in decrypted_data:
                        for i, c in enumerate(decrypted_data["cuentas"]):
                            if not isinstance(c, dict):
                                continue
                            for field in SENSITIVE_FIELDS:
                                enc_key = f"{field}_encriptado"
                                if enc_key in c and c[enc_key]:
                                    raw = c[enc_key]
                                    enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                                    decrypted = _decrypt_value_safe(enc_bytes)
                                    if decrypted:
                                        decrypted_data["cuentas"][i] = dict(decrypted_data["cuentas"][i])
                                        decrypted_data["cuentas"][i][field] = decrypted
                    else:
                        for field in SENSITIVE_FIELDS:
                            enc_key = f"{field}_encriptado"
                            if enc_key in data and data[enc_key]:
                                raw = data[enc_key]
                                enc_bytes = bytes.fromhex(raw) if isinstance(raw, str) else raw
                                decrypted = _decrypt_value_safe(enc_bytes)
                                decrypted_data[field] = decrypted if decrypted else data.get(field)
                            elif field in data and data[field] is not None:
                                decrypted_data[field] = data[field]
                    update_from_api(decrypted_data)"""
    if new_sync in content:
        return False
    content = content.replace(old_sync, new_sync)

    # update_from_api: also store _cuentas_data when data has "cuentas"
    old_update = """def update_from_api(data: dict[str, Any]) -> None:
    \"\"\"Actualiza el holder desde la API de configuraci\u00f3n (PUT /configuracion/email/configuracion).\"\"\"
    keys = (
        "smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name",
        "tickets_notify_emails", "modo_pruebas", "email_pruebas", "emails_pruebas", "email_activo",
        "email_activo_notificaciones", "email_activo_informe_pagos", "email_activo_estado_cuenta",
        "email_activo_cobros", "email_activo_campanas", "email_activo_tickets",
        "modo_pruebas_notificaciones", "modo_pruebas_informe_pagos", "modo_pruebas_estado_cuenta",
        "modo_pruebas_cobros", "modo_pruebas_campanas", "modo_pruebas_tickets",
        "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl",
    )
    for k in keys:
        if k in data and data[k] is not None:
            _current[k] = data[k]
    if "smtp_port" in data and data["smtp_port"] is not None:
        _current["smtp_port"] = str(data["smtp_port"])"""
    # Use a simpler replacement: add at the start of update_from_api the handling of version 2
    if " _cuentas_data[" in content and "cuentas" in content:
        pass  # already patched
    else:
        content = content.replace(
            'def update_from_api(data: dict[str, Any]) -> None:\n    """Actualiza el holder desde la API de configuraci',
            'def update_from_api(data: dict[str, Any]) -> None:\n    """Actualiza el holder desde la API de configuracion (PUT /configuracion/email/configuracion). Soporta version 2 (4 cuentas)."""\n    global _cuentas_data\n    if data.get("version") == 2 and "cuentas" in data:\n        _cuentas_data.clear()\n        _cuentas_data["version"] = 2\n        _cuentas_data["cuentas"] = [dict(c) for c in data["cuentas"]]\n        _cuentas_data["asignacion"] = dict(data.get("asignacion") or {})\n        # _current = primera cuenta + flags globales\n        if data["cuentas"]:\n            for k, v in data["cuentas"][0].items():\n                if k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl", "smtp_use_tls"):\n                    _current[k] = v\n        for k in ("modo_pruebas", "email_pruebas", "emails_pruebas", "email_activo", "tickets_notify_emails", "email_activo_notificaciones", "email_activo_informe_pagos", "email_activo_estado_cuenta", "email_activo_cobros", "email_activo_campanas", "email_activo_tickets", "modo_pruebas_notificaciones", "modo_pruebas_informe_pagos", "modo_pruebas_estado_cuenta", "modo_pruebas_cobros", "modo_pruebas_campanas", "modo_pruebas_tickets"):\n            if k in data and data[k] is not None:\n                _current[k] = data[k]\n        if _current.get("smtp_port") is not None:\n            _current["smtp_port"] = str(_current["smtp_port"])\n        return\n    """Actualiza el holder desde la API de configuraci',
        )

    # get_smtp_config: add servicio and tipo_tab and use _cuentas_data when available
    old_get = """def get_smtp_config() -> dict[str, Any]:
    \"\"\"Devuelve la config SMTP actual. Siempre carga desde BD primero para usar el correo guardado en Configuraci\u00f3n > Email (no el de .env).\"\"\"
    sync_from_db()
    if _current.get("smtp_user"):"""
    new_get = """def get_smtp_config(servicio: Optional[str] = None, tipo_tab: Optional[str] = None) -> dict[str, Any]:
    \"\"\"Devuelve la config SMTP para el servicio/tab. Cobros=cuenta 1, Estado cuenta=2, Notificaciones=cuenta por tab (3 o 4).\"\"\"
    sync_from_db()
    if servicio and _cuentas_data.get("cuentas"):
        asignacion = _cuentas_data.get("asignacion") or {}
        idx = obtener_indice_cuenta(servicio, tipo_tab, asignacion)
        idx = max(1, min(idx, NUM_CUENTAS))
        c = _cuentas_data["cuentas"][idx - 1]
        if isinstance(c, dict) and (c.get("smtp_user") or "").strip():
            return {
                "smtp_host": c.get("smtp_host") or "",
                "smtp_port": int(c.get("smtp_port") or 587),
                "smtp_user": c.get("smtp_user") or "",
                "smtp_password": c.get("smtp_password") or "",
                "from_email": c.get("from_email") or c.get("smtp_user") or "",
                "from_name": c.get("from_name") or "RapiCredit",
                "smtp_use_tls": c.get("smtp_use_tls", "true"),
            }
    if _current.get("smtp_user"):"""
    if "obtener_indice_cuenta" in content and "get_smtp_config(servicio" in content:
        return False
    content = content.replace(old_get, new_get)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    os.chdir(ROOT)
    changed = patch_email_config_holder()
    print("email_config_holder.py:", "updated" if changed else "no change or already patched")
    print("Listo. Revisa backend/app/core/email_config_holder.py y ejecuta tests.")


if __name__ == "__main__":
    main()
