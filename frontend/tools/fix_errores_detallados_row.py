from __future__ import annotations

import pathlib
import re

p = pathlib.Path(__file__).resolve().parents[1] / "src/components/carga-masiva/ErroresDetallados.tsx"
t = p.read_text(encoding="utf-8")

pat = r"return\s*\[\s*error\.cedula,\s*String\(error\.data\.nombre \? error\.data\.fecha \?\? ''\),\s*String\(error\.data\.telefono \? error\.data\.monto_pagado \?\? ''\),\s*String\(error\.data\.email \? error\.data\.documento_pago \?\? ''\),\s*error\.error,"

repl = """return [
        error.cedula,
        ...(tipo === 'clientes'
          ? [
              String(error.data.nombre ?? ''),
              String(error.data.telefono ?? ''),
              String(error.data.email ?? ''),
            ]
          : [
              String(error.data.fecha ?? ''),
              String(error.data.monto_pagado ?? ''),
              String(error.data.documento_pago ?? ''),
            ]),
        error.error,"""

t2, n = re.subn(pat, repl, t, count=1, flags=re.DOTALL)
print("matches", n)
if n:
    p.write_text(t2, encoding="utf-8")
