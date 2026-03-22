from pathlib import Path

p = Path(__file__).resolve().parent / "backend" / "app" / "services" / "diagnostico_critico_service.py"
t = p.read_text(encoding="utf-8")
old = 'motivo=f"Correccion de sobre-aplicacion: reduccion de {exceso}"'
new = 'motivo=f"Corrección de sobre-aplicación: reducción de {exceso}"'
if old not in t:
    raise SystemExit("old motivo not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
