# Auditoria: 1) Normalizar body_text a UTF-8; 2) Validar cfg SMTP antes de usar
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Tras has_attachments y cfg = get_smtp_config(), anadir validacion de cfg
old_cfg = "    has_attachments = bool(attachments)\n    cfg = get_smtp_config()\n\n    try:"
new_cfg = """    has_attachments = bool(attachments)
    cfg = get_smtp_config()
    if not cfg.get("smtp_host") or not cfg.get("smtp_user"):
        return False, "No hay servidor SMTP configurado. Configura en Configuracion > Email."
    if not (cfg.get("smtp_password") or "").strip() or (cfg.get("smtp_password") or "").strip() == "***":
        return False, "Falta contrasena SMTP. Configura en Configuracion > Email."

    try:"""
if new_cfg.strip() in c and "No hay servidor SMTP" in c:
    print("cfg validation already present")
else:
    c = c.replace(old_cfg, new_cfg)
    print("Added cfg validation")

# 2) Normalizar body_text a UTF-8 al inicio del try (consistencia con body_html)
old_try = """    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        # Asegurar body_html es str y UTF-8 valido"""
new_try = """    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        # Asegurar body_text y body_html son str y UTF-8 validos
        if body_text is None:
            body_text = ""
        if isinstance(body_text, bytes):
            try:
                body_text = body_text.decode("utf-8")
            except UnicodeDecodeError:
                body_text = body_text.decode("cp1252", errors="replace")
        else:
            try:
                body_text.encode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                body_text = body_text.encode("utf-8", errors="replace").decode("utf-8")
        # Asegurar body_html es str y UTF-8 valido"""
if "body_text es str y UTF-8" in c:
    print("body_text normalization already present")
else:
    c = c.replace(old_try, new_try)
    print("Added body_text UTF-8 normalization")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
