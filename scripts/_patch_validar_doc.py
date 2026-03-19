# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
t = p.read_text(encoding="utf-8")
old = (
    '    """\n'
    "    Valida cédula (formato V/E/J + dígitos) y verifica si tiene préstamo.\n"
    "    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.\n"
    "    Sin límite cuando origen=infopagos (ruta /pagos/infopagos, uso interno).\n"
    '    """'
)
new = (
    '    """\n'
    "    Valida cédula (formato V/E/J + dígitos), existencia en clientes y un único préstamo APROBADO\n"
    "    (misma regla que la importación a la tabla pagos).\n"
    "    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.\n"
    "    Sin límite cuando origen=infopagos (ruta /pagos/infopagos, uso interno).\n"
    '    """'
)
if old not in t:
    raise SystemExit("docstring block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
