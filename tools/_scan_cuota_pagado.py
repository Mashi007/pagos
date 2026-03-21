from pathlib import Path

root = Path(__file__).resolve().parents[1] / "backend" / "app"
for p in root.rglob("*.py"):
    t = p.read_text(encoding="utf-8", errors="replace")
    for i, l in enumerate(t.splitlines(), 1):
        if "Cuota.estado" in l and ("PAGADO" in l or "PAGO_ADELANTADO" in l):
            if "==" in l or "!=" in l or "in_" in l:
                print(f"{p.relative_to(root)}:{i}:{l.strip()[:120]}")
