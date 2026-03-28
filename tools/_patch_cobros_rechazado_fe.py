from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/pages/CobrosPagosReportadosPage.tsx"
t = p.read_text(encoding="utf-8")

repls = [
    (
        """ * Vista por defecto (sin filtro de estado): el API no devuelve aprobados ni importados; al aprobar la fila desaparece y el Excel agrupa aprobados pendientes de exportar.""",
        """ * Vista por defecto (sin filtro de estado): el API no devuelve aprobados, importados ni rechazados; los rechazados solo con filtro o tarjeta Rechazado. Al aprobar, la fila desaparece y el Excel agrupa aprobados pendientes de exportar.""",
    ),
    (
        """              <option value="">
                Por gestionar (excluye aprobados e importados)
              </option>""",
        """              <option value="">
                Por gestionar (excluye aprobados, importados y rechazados)
              </option>""",
    ),
    (
        """              La opciA3n por defecto coincide con el listado: al aprobar, la fila
              deja de mostrarse aquA- y pasa al Excel &quot;Descargar Excel
              Aprobados&quot;. Si elige &quot;Aprobado&quot; en el filtro, las
              filas aprobadas siguen visibles hasta exportarlas.""",
        """              La opciA3n por defecto coincide con el listado: al aprobar, la fila
              deja de mostrarse aquA- y pasa al Excel &quot;Descargar Excel
              Aprobados&quot;. Los rechazados no se listan aquA-: use la tarjeta o el filtro
              &quot;Rechazado&quot;. Si elige &quot;Aprobado&quot; en el filtro, las
              filas aprobadas siguen visibles hasta exportarlas.""",
    ),
]

# File may use proper UTF-8 for Spanish - check option block
if "Por gestionar (excluye aprobados e importados)" not in t:
    # try UTF-8 proper
    alt = "Por gestionar (excluye aprobados e importados)"
    if alt not in t:
        raise SystemExit("option text not found")

for old, new in repls:
    if old not in t:
        raise SystemExit("missing block:\n" + old[:120])
    t = t.replace(old, new, 1)

old_btn = """            title="Misma vista que el filtro por defecto: pendiente, en revisiA3n y rechazado (sin aprobados ni importados)."
            className={
              'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
              (estado === ''
                ? 'border-primary bg-primary/10 font-semibold'
                : 'border-muted hover:bg-muted/50')
            }
          >
            <span className="block text-xs uppercase tracking-wide text-muted-foreground">
              Por gestionar
            </span>

            <span className="text-2xl font-bold">
              {kpis.pendiente + kpis.en_revision + kpis.rechazado}
            </span>"""

new_btn = """            title="Cola operativa: pendiente y en revisiA3n (sin aprobados, importados ni rechazados). Ver rechazados con la tarjeta Rechazado o el filtro."
            className={
              'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
              (estado === ''
                ? 'border-primary bg-primary/10 font-semibold'
                : 'border-muted hover:bg-muted/50')
            }
          >
            <span className="block text-xs uppercase tracking-wide text-muted-foreground">
              Por gestionar
            </span>

            <span className="text-2xl font-bold">
              {kpis.pendiente + kpis.en_revision}
            </span>"""

if old_btn not in t:
    raise SystemExit("kpi button block not found")
t = t.replace(old_btn, new_btn, 1)

p.write_text(t, encoding="utf-8")
print("ok frontend")
