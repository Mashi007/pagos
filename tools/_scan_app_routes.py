from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.tsx"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
print("lines", len(lines))
for i, line in enumerate(lines):
    if "rapicredit-estadocuenta" in line:
        for j in range(max(0, i - 2), min(len(lines), i + 12)):
            print(f"{j+1}|{lines[j]}")
        print("---")
    if 'path="/informes"' in line.replace("'", '"') or "path='/informes'" in line or 'path="/pagos/informes"' in line:
        for j in range(max(0, i - 2), min(len(lines), i + 12)):
            print(f"{j+1}|{lines[j]}")
        print("===informes===")
