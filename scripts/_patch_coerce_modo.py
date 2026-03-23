from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "notificaciones_envios_store.py"
t = p.read_text(encoding="utf-8")
old = """    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes", "si", "sA-")"""
new = """    if isinstance(raw, str):
        s = raw.strip().lower()
        return s in ("true", "1", "yes", "si", "sí", "on")"""
if old not in t:
    raise SystemExit("pattern not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
