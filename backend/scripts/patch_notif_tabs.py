# Patch notificaciones_tabs to pass tipo_tab to send_email
import os
path = os.path.join(os.path.dirname(__file__), "..", "app", "api", "v1", "endpoints", "notificaciones_tabs.py")
path = os.path.abspath(path)
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

old = """        if to_email:
            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
            )"""
new = """        if to_email:
            tipo_tab_envio = _tipo_tab_para_persistencia(tipo)
            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
                tipo_tab=tipo_tab_envio,
            )"""
if old in c:
    c = c.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("notificaciones_tabs.py patched")
else:
    print("Block not found")
