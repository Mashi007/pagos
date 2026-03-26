from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "core" / "scheduler.py"
t = p.read_text(encoding="utf-8")
old = 'name="Campañas CRM programadas (cada 1 min)"'
new = 'name="Campanas CRM programadas (cada 1 min)"'
if old not in t:
    raise SystemExit(f"pattern not found. Snippet: {t[t.find('Camp'):t.find('Camp')+80]!r}")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched scheduler")
