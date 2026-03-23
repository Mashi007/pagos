from pathlib import Path

p = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/services/notificacionService.ts"
)
t = p.read_text(encoding="utf-8")
old = "      ${this.baseUrl}/enviar-prueba-paquete,"
new = "      `${this.baseUrl}/enviar-prueba-paquete`,"
if old not in t:
    raise SystemExit("pattern not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
