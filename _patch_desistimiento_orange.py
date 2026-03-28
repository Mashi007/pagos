# -*- coding: utf-8 -*-
from pathlib import Path

repls = [
    (
        Path("frontend/src/components/prestamos/PrestamosList.tsx"),
        "DESISTIMIENTO: 'bg-slate-200 text-slate-800 border-slate-400',",
        "DESISTIMIENTO: 'bg-orange-100 text-orange-900 border-orange-400',",
    ),
    (
        Path("frontend/src/components/finiquito/FiniquitoRevisionDialog.tsx"),
        "if (e === 'DESISTIMIENTO') return 'bg-slate-200 text-slate-800'",
        "if (e === 'DESISTIMIENTO') return 'bg-orange-100 text-orange-900'",
    ),
]

for path, old, new in repls:
    t = path.read_text(encoding="utf-8")
    if new in t:
        print(path, "already")
        continue
    assert old in t, f"missing in {path}"
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print(path, "OK")

pd = Path("frontend/src/components/prestamos/PrestamoDetalleModal.tsx")
t = pd.read_text(encoding="utf-8")
if "DESISTIMIENTO: 'bg-orange-100" not in t:
    o1 = """      LIQUIDADO: 'bg-gray-100 text-gray-800 border-gray-300',

      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }"""
    n1 = """      LIQUIDADO: 'bg-gray-100 text-gray-800 border-gray-300',

      DESISTIMIENTO: 'bg-orange-100 text-orange-900 border-orange-400',

      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }"""
    assert o1 in t, "PrestamoDetalleModal badges block"
    t = t.replace(o1, n1, 1)
    o2 = """      LIQUIDADO: 'Liquidado',

      RECHAZADO: 'Rechazado',
    }"""
    n2 = """      LIQUIDADO: 'Liquidado',

      DESISTIMIENTO: 'Desistimiento',

      RECHAZADO: 'Rechazado',
    }"""
    assert o2 in t, "PrestamoDetalleModal labels block"
    t = t.replace(o2, n2, 1)
    pd.write_text(t, encoding="utf-8")
    print(pd, "OK")
else:
    print(pd, "already")

print("done")
