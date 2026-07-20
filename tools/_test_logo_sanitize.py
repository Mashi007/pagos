# -*- coding: utf-8 -*-
import re
from pathlib import Path

src = Path("backend/app/core/email.py").read_text(encoding="utf-8")
start = src.find("def _sanitize_html_for_email")
end = src.find("def preparar_body_html_para_mime")
ns = {"re": re}
exec("_MIN_BASE64_LENGTH_TO_REPLACE = 300\n" + src[start:end], ns)
logo = "https://rapicredit.onrender.com/pagos/logos/rapicredit-public.png"
html = '<img src="{{logo_url}}" alt="Rapicredit" width="320">'
out = ns["_sanitize_html_for_email"](html, logo)
assert "{{logo_url}}" not in out, out
assert logo in out, out
print(out)
print("OK")
