from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "core" / "scheduler.py"
t = p.read_text(encoding="utf-8")
for line in t.splitlines():
    if "name=" in line and "CRM programadas" in line:
        before = line
        break
else:
    raise SystemExit("name line not found")
# Normalizar a ASCII para logs (evita mojibake en algunos viewers).
line2 = before.replace("Campañas CRM", "Campanas CRM")
if line2 == before:
    # Si el archivo ya estaba en ASCII u otro encoding raro, reemplazar por patron de comillas.
    import re

    line2 = re.sub(r'name="[^"]*CRM programadas[^"]*"', 'name="Campanas CRM programadas (cada 1 min)"', before)
t = t.replace(before, line2)
p.write_text(t, encoding="utf-8")
print("ok:", line2.strip())
