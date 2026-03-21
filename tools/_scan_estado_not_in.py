from pathlib import Path

root = Path(__file__).resolve().parents[1] / "backend" / "app"
for p in root.rglob("*.py"):
    t = p.read_text(encoding="utf-8", errors="replace")
    if "estado NOT IN" in t and "cuotas" in t.lower():
        for i, l in enumerate(t.splitlines(), 1):
            if "estado NOT IN" in l and "cuota" in l.lower():
                print(f"{p.relative_to(root)}:{i}:{l.strip()[:100]}")
