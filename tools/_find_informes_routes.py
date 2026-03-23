from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.tsx"
for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    low = line.lower()
    if "rapicredit-estadocuenta" in low or "informes" in low or "estadocuenta" in low:
        if "route" in low or "element" in low or "lazy" in low or "import" in low:
            print(f"{i}|{line[:160]}")
