from pathlib import Path
p = Path("frontend/src/components/prestamos/PrestamosList.tsx")
t = p.read_text(encoding="utf-8")
t = t.replace(
    "'LIQUIDADO',\n    ].includes(estadoFromUrl)",
    "'LIQUIDADO',\n      'DESISTIMIENTO',\n    ].includes(estadoFromUrl)",
    1,
)
t = t.replace(
    "'LIQUIDADO',\n      ].includes(estadoParam)",
    "'LIQUIDADO',\n        'DESISTIMIENTO',\n      ].includes(estadoParam)",
    1,
)
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
        '<SelectItem value="RECHAZADO">Rechazado</SelectItem>',
        '<SelectItem value="DESISTIMIENTO">Desistimiento</SelectItem>\n\n                      <SelectItem value="RECHAZADO">Rechazado</SelectItem>',
        1,
    )
p.write_text(t, encoding="utf-8", newline="\n")
print("ok")
