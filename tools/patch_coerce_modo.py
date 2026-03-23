import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "notificaciones_envios_store.py"
t = p.read_text(encoding="utf-8", errors="replace")
pattern = r"    if isinstance\(raw, str\):\r?\n        return raw\.strip\(\)\.lower\(\) in \([^)]+\)"
repl = """    if isinstance(raw, str):
        s = raw.strip().lower()
        return s in ("true", "1", "yes", "si", "sí", "on")"""
new_t, n = re.subn(pattern, repl, t, count=1)
if n != 1:
    raise SystemExit(f"replace count={n}")
p.write_text(new_t, encoding="utf-8")
print("ok")
