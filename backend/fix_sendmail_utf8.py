# Fix: smtplib.sendmail() does msg.encode('ascii') so Unicode (e.g. i-acute) fails.
# Pass bytes (UTF-8) and fix EOLs for SMTP.
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace both sendmail lines to use UTF-8 bytes
old1 = 'server.sendmail(msg["From"], all_recipients, msg.as_string(policy=__import__("email").policy.SMTP))'
new1 = 'msg_str = msg.as_string(policy=__import__("email").policy.SMTP); msg_bytes = msg_str.replace("\\r\\n", "\\n").replace("\\n", "\\r\\n").encode("utf-8"); server.sendmail(msg["From"], all_recipients, msg_bytes)'

if old1 not in c:
    print("Pattern not found")
    exit(1)
c = c.replace(old1, new1)
# Replace second occurrence (the one in the else branch)
c = c.replace(old1, new1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: sendmail now uses UTF-8 bytes")
