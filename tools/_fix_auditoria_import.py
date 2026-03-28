from pathlib import Path

p = Path("frontend/src/App.tsx")
t = p.read_text(encoding="utf-8")
old = "import Auditoria from './pages/Auditoria'"
new = "import Auditoria from './pages/Auditoria.tsx'"
if old not in t:
    raise SystemExit(f"pattern not found: {old!r}")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("App.tsx now imports Auditoria.tsx explicitly")
