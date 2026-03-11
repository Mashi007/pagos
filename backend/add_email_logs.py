"""Anade logs de diagnostico al flujo de email (sin escribir contrasenas)."""
from pathlib import Path

# 1) configuracion_email.py - log tras persistir
p1 = Path("app/api/v1/endpoints/configuracion_email.py")
t1 = p1.read_text(encoding="utf-8")
old1 = """    update_from_api(_email_config_stub)
    _persist_email_config(db)
    logger.info("Configuracion email actualizada y persistida en BD (campos: %s)", list(data.keys()))
    resp = {"""
new1 = """    update_from_api(_email_config_stub)
    _persist_email_config(db)
    stub_pw = _email_config_stub.get("smtp_password") or ""
    logger.info(
        "Configuracion email persistida (campos: %s). password_skipped=%s, smtp_password_len=%s",
        list(data.keys()), password_skipped, len(stub_pw) if stub_pw and stub_pw != "***" else 0,
    )
    resp = {"""
if old1 in t1 and "smtp_password_len" not in t1:
    t1 = t1.replace(old1, new1, 1)
    p1.write_text(t1, encoding="utf-8")
    print("configuracion_email: log anadido")
else:
    print("configuracion_email: ya tiene log o no encontrado")

# 2) email.py - log antes de server.login
p2 = Path("app/core/email.py")
t2 = p2.read_text(encoding="utf-8")
old2 = """        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        if port == 465:"""
new2 = """        port = int(cfg.get("smtp_port") or 587)
        all_recipients = to_emails + cc_list + bcc_list
        use_tls = (cfg.get("smtp_use_tls") or "true").lower() == "true"
        pw = (cfg.get("smtp_password") or "").strip()
        logger.info(
            "send_email: %s:%s user=%s smtp_password_len=%s (0=vacío)",
            cfg.get("smtp_host"), port, cfg.get("smtp_user"), len(pw),
        )
        if port == 465:"""
if old2 in t2 and "smtp_password_len" not in t2:
    t2 = t2.replace(old2, new2, 1)
    p2.write_text(t2, encoding="utf-8")
    print("email.py: log anadido")
else:
    print("email.py: ya tiene log o no encontrado")

# 3) email_config_holder.py - log en sync_from_db tras cargar
p3 = Path("app/core/email_config_holder.py")
t3 = p3.read_text(encoding="utf-8")
# Necesitamos import logging y logger si no existen
if "import logging" not in t3:
    t3 = t3.replace("import json\n", "import json\nimport logging\n", 1)
    t3 = t3.replace("CLAVE_EMAIL_CONFIG = ", "logger = logging.getLogger(__name__)\n\nCLAVE_EMAIL_CONFIG = ", 1)
if "update_from_api(decrypted_data)" in t3 and "sync_from_db" in t3:
    old3 = "                    update_from_api(decrypted_data)\n        finally:"
    pw_len = "len(decrypted_data.get('smtp_password') or '') if decrypted_data.get('smtp_password') else 0"
    new3 = """                    update_from_api(decrypted_data)
                    logger.info("sync_from_db: config cargada desde BD, smtp_password_len=%s", %s)
        finally:""" % (pw_len, pw_len)
    # Fix: log only one value
    new3 = """                    update_from_api(decrypted_data)
                    _pw = (decrypted_data.get("smtp_password") or "")
                    logger.info("sync_from_db: cargado desde BD, smtp_password_len=%s", len(_pw) if _pw else 0)
        finally:"""
    if "sync_from_db: cargado" not in t3:
        t3 = t3.replace("                    update_from_api(decrypted_data)\n        finally:", new3, 1)
        p3.write_text(t3, encoding="utf-8")
        print("email_config_holder: log en sync_from_db anadido")
    else:
        print("email_config_holder: ya tiene log")
else:
    print("email_config_holder: bloque no encontrado")

# 4) email_config_holder prepare_for_db_storage - log si encripto o no
if "prepare_for_db_storage" in t3:
    p3 = Path("app/core/email_config_holder.py")
    t3 = p3.read_text(encoding="utf-8")
    old4 = "            encrypted = _encrypt_value_safe(result[field], field)\n            if encrypted:"
    new4 = """            encrypted = _encrypt_value_safe(result[field], field)
            logger.info("prepare_for_db_storage: %s encriptado=%s", field, encrypted is not None)
            if encrypted:"""
    if old4 in t3 and "prepare_for_db_storage:" not in t3:
        t3 = t3.replace(old4, new4, 1)
        p3.write_text(t3, encoding="utf-8")
        print("email_config_holder: log en prepare_for_db_storage anadido")

print("Listo.")
