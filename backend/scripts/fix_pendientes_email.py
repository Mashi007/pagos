# Fix pendientes: 1) duplicate return en email_config_holder 2) configuracion_email_cuentas import + _mask_cuenta
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
core = os.path.join(root, "app", "core")
endpoints = os.path.join(root, "app", "api", "v1", "endpoints")

# 1) email_config_holder: remove duplicate "return (modo, [])"
path1 = os.path.join(core, "email_config_holder.py")
with open(path1, "r", encoding="utf-8", errors="replace") as f:
    c1 = f.read()
old1 = """    if modo:
        return (modo, _get_emails_pruebas_list())
    return (modo, [])

    return (modo, [])


def get_modo_pruebas_servicio"""
new1 = """    if modo:
        return (modo, _get_emails_pruebas_list())
    return (modo, [])


def get_modo_pruebas_servicio"""
if old1 in c1:
    c1 = c1.replace(old1, new1, 1)
    with open(path1, "w", encoding="utf-8") as f:
        f.write(c1)
    print("email_config_holder: removed duplicate return")
else:
    print("email_config_holder: pattern not found or already fixed")

# 2) configuracion_email_cuentas: remove _decrypt_value_safe import
path2 = os.path.join(endpoints, "configuracion_email_cuentas.py")
with open(path2, "r", encoding="utf-8", errors="replace") as f:
    c2 = f.read()
if "_decrypt_value_safe" in c2:
    c2 = c2.replace(
        "    update_from_api,\n    _decrypt_value_safe,\n)",
        "    update_from_api,\n)",
        1
    )
    with open(path2, "w", encoding="utf-8") as f:
        f.write(c2)
    print("configuracion_email_cuentas: removed unused _decrypt_value_safe import")
else:
    print("configuracion_email_cuentas: import already clean")

# 3) _mask_cuenta: exclude _encriptado keys
old3 = """def _mask_cuenta(c: dict) -> dict:
    out = dict(c)
    for f in SENSITIVE_FIELDS:
        if out.get(f):
            out[f] = "***"
    return out"""
new3 = '''def _mask_cuenta(c: dict) -> dict:
    """Copia la cuenta enmascarando contraseñas y sin exponer campos _encriptado."""
    out = {k: v for k, v in c.items() if not k.endswith("_encriptado")}
    for f in SENSITIVE_FIELDS:
        if out.get(f):
            out[f] = "***"
    return out'''
if old3 in c2 and "encriptado" not in (open(path2).read().split("_mask_cuenta")[1][:400]):
    with open(path2, "r", encoding="utf-8") as f:
        c2 = f.read()
    c2 = c2.replace(old3, new3, 1)
    with open(path2, "w", encoding="utf-8") as f:
        f.write(c2)
    print("configuracion_email_cuentas: _mask_cuenta now excludes _encriptado")
else:
    with open(path2, "r", encoding="utf-8") as f:
        c2 = f.read()
    if "_encriptado" in c2 and "def _mask_cuenta" in c2:
        if "encriptado" not in c2[c2.find("def _mask_cuenta"):c2.find("def _mask_cuenta")+500]:
            c2 = c2.replace(
                "def _mask_cuenta(c: dict) -> dict:\n    out = dict(c)",
                'def _mask_cuenta(c: dict) -> dict:\n    """Copia la cuenta enmascarando contraseñas y sin exponer campos _encriptado."""\n    out = {k: v for k, v in c.items() if not k.endswith("_encriptado")}',
                1
            )
            with open(path2, "w", encoding="utf-8") as f:
                f.write(c2)
            print("configuracion_email_cuentas: _mask_cuenta updated (variant)")
    else:
        print("configuracion_email_cuentas: _mask_cuenta already improved or not found")

print("Done.")
