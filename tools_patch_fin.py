from pathlib import Path
p = Path("frontend/src/components/finiquito/FiniquitoRevisionDialog.tsx")
t = p.read_text(encoding="utf-8")
if "DESISTIMIENTO" not in t:
    t = t.replace(
        "  if (e === 'RECHAZADO') return 'bg-red-100 text-red-800'\n",
        "  if (e === 'DESISTIMIENTO') return 'bg-slate-200 text-slate-800'\n  if (e === 'RECHAZADO') return 'bg-red-100 text-red-800'\n",
        1,
    )
    t = t.replace(
        "  if (e === 'RECHAZADO') return 'Rechazado'\n",
        "  if (e === 'DESISTIMIENTO') return 'Desistimiento'\n  if (e === 'RECHAZADO') return 'Rechazado'\n",
        1,
    )
    p.write_text(t, encoding="utf-8", newline="\n")
    print("finiquito ok")
else:
    print("skip")
