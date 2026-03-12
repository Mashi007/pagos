# Patch email.py: normalize body_html to valid UTF-8 before MIME; use SMTP policy for as_string
import os

path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add helper and use it before MIMEText
old_sanitize = """        # Corregir data URLs mal formadas (base64/ -> base64,) para que el HTML se renderice
        if body_html and "base64/" in body_html:
            body_html = body_html.replace("base64/", "base64,")"""

new_sanitize = '''        # Asegurar body_html es str y UTF-8 valido (evita HTML corrupto por encoding BD/plantilla)
        if body_html is not None:
            if isinstance(body_html, bytes):
                try:
                    body_html = body_html.decode("utf-8")
                except UnicodeDecodeError:
                    body_html = body_html.decode("cp1252", errors="replace")
            else:
                try:
                    body_html.encode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    body_html = body_html.encode("utf-8", errors="replace").decode("utf-8")
            if "base64/" in body_html:
                body_html = body_html.replace("base64/", "base64,")'''

if new_sanitize in content:
    print("Already patched (encoding)")
else:
    content = content.replace(old_sanitize, new_sanitize)
    print("Patched encoding block")

# 2) Use policy for as_string so SMTP line lengths are correct
old_send = 'server.sendmail(msg["From"], all_recipients, msg.as_string())'
new_send = 'server.sendmail(msg["From"], all_recipients, msg.as_string(policy=__import__("email").policy.SMTP))'
# Replace both occurrences (port 465 and else)
content = content.replace(old_send, new_send)

if "policy=__import__" in content:
    print("Patched as_string policy")
else:
    # try alternative
    content = content.replace("msg.as_string())", "msg.as_string(policy=__import__(\"email\").policy.SMTP))")
    print("Patched as_string (alt)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done:", path)
