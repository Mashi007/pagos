# Gmail y otros clientes esperan cabecera Date
import os
from datetime import datetime
from email.utils import formatdate
path = os.path.join(os.path.dirname(__file__), "app", "core", "email.py")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
old = '        msg["Subject"] = subject\n        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")'
new = '        msg["Subject"] = subject\n        msg["From"] = cfg.get("from_email") or cfg.get("smtp_user")\n        msg["Date"] = formatdate(localtime=True)'
if 'msg["Date"]' in c:
    print("Date already set")
else:
    c = c.replace(old, new)
    # ensure formatdate is imported (email.utils)
    if "formatdate" not in c and "from email.utils import formatdate" not in c:
        c = c.replace("from email import encoders", "from email import encoders\n        from email.utils import formatdate")
    # formatdate is used inside try - so we need to import at top level
    if "from email.utils import formatdate" not in c[:3000]:
        c = c.replace("from email import encoders", "from email.utils import formatdate\nfrom email import encoders")
    c = c.replace("from email.utils import formatdate\nfrom email import encoders", "from email import encoders")
    c = c.replace("        from email.utils import formatdate", "")
    if "formatdate" in c and "email.utils" not in c.split("def send_email")[0]:
        c = c.replace("from email.mime.base import MIMEBase", "from email.mime.base import MIMEBase\nfrom email.utils import formatdate")
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Added Date header")
print("Done")
