"""One-off: dedupe repeated security_headers + auth_csrf_cookies imports in main.py."""
from pathlib import Path

path = Path(__file__).resolve().parent / "app/main.py"
text = path.read_text(encoding="utf-8")
dup = """
# Importar middlewares de seguridad FASE 1
from app.middleware.security_headers import (
    SecurityHeadersMiddleware,
    ContentSecurityPolicyMiddleware,
    RequestIdMiddleware,
)
from app.api.v1.endpoints import auth_csrf_cookies

"""
if text.count(dup) < 2:
    raise SystemExit(f"expected 2 duplicate blocks, found {text.count(dup)}")
text = text.replace(dup, dup, 1)  # keep first
text = text.replace(dup, "\n", 1)  # remove second block (leave one newline)
path.write_text(text, encoding="utf-8")
print("main.py imports deduped")
