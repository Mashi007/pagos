from pathlib import Path

p = Path("frontend/src/components/prestamos/PrestamosList.tsx")
t = p.read_text(encoding="utf-8")
pairs = [
    (
        "'LIQUIDADO',\n      'RECHAZADO',\n    ].includes(estadoFromUrl)",
        "'LIQUIDADO',\n      'RECHAZADO',\n      'DESISTIMIENTO',\n    ].includes(estadoFromUrl)",
    ),
    (
        "'LIQUIDADO',\n        'RECHAZADO',\n      ].includes(estadoParam)",
        "'LIQUIDADO',\n        'RECHAZADO',\n        'DESISTIMIENTO',\n      ].includes(estadoParam)",
    ),
]
for old, new in pairs:
    if old not in t:
        raise SystemExit(f"missing: {old[:50]}")
    t = t.replace(old, new, 1)

if "DESISTIMIENTO:" not in t:
    t = t.replace(
        "      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',\n",
        "      DESISTIMIENTO: 'bg-slate-200 text-slate-800 border-slate-400',\n\n      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',\n",
        1,
    )
    t = t.replace(
        "      RECHAZADO: 'Rechazado',\n",
        "      DESISTIMIENTO: 'Desistimiento',\n\n      RECHAZADO: 'Rechazado',\n",
        1,
    )

if 'value="DESISTIMIENTO"' not in t:
    t = t.replace(
        '<SelectItem \n                      value="RECHAZADO">Rechazado</SelectItem>',
        '<SelectItem \n                      value="DESISTIMIENTO">Desistimiento</SelectItem>\n\n                      <SelectItem \n                      value="RECHAZADO">Rechazado</SelectItem>',
        1,
    )

p.write_text(t, encoding="utf-8", newline="\n")
print("PrestamosList ok")
