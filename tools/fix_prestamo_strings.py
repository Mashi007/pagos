# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("frontend/src/services/prestamoService.ts")
t = p.read_text(encoding="utf-8", errors="replace")

t = t.replace(
    "throw new Error(\n        'La respuesta no es un PDF de estado de cuenta (se recibió Excel). Actualice la aplicación o revise el despliegue.'\n      )",
    "throw new Error(\n        'La respuesta no es un PDF de estado de cuenta (se recibio Excel). Actualice la aplicacion o revise el despliegue.'\n      )",
)

# Also fix any mojibake variants
for bad, good in [
    ("se recibió", "se recibio"),
    ("aplicación", "aplicacion"),
    ("válido", "valido"),
    ("sesión", "sesion"),
]:
    t = t.replace(bad, good)

p.write_text(t, encoding="utf-8")
print("done")
