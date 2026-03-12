# Fix email.py: 1) correct MIME structure (alternative inside mixed when attachments);
# 2) fix malformed data URLs (base64/ -> base64,) so HTML renders
import os

path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart("mixed" if has_attachments else "alternative")
        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")
        msg["To"] = ", ".join(to_emails)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        if has_attachments:'''

new = '''    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        # Corregir data URLs mal formadas (base64/ -> base64,) para que el HTML se renderice
        if body_html and "base64/" in body_html:
            body_html = body_html.replace("base64/", "base64,")

        if has_attachments:
            msg = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                alt.attach(MIMEText(body_html, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")
        msg["To"] = ", ".join(to_emails)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if bcc_list:
            msg["Bcc"] = ", ".join(bcc_list)

        if has_attachments:'''

if old not in content:
    print("Block not found (maybe already patched?)")
    exit(1)
content = content.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("email.py: MIME structure fixed and base64/ -> base64, applied")
