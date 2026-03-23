from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
t = p.read_text(encoding="utf-8")
old = 'cedula_cliente=cedula.strip().upper() if cedula else "",  # Normalize to uppercase'
new = "cedula_cliente=cedula_fk"
if old not in t:
    raise SystemExit("old string not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
print("OK")
