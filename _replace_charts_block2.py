from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardPagos.tsx"
)
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
start_idx = end_idx = None
for i, l in enumerate(lines):
    if "PRINCIPALES" in l and "KPI" not in l and "GR" in l:
        start_idx = i
    if "BOTONES EXPLORAR DETALLES" in l:
        end_idx = i
        break
if start_idx is None or end_idx is None:
    raise SystemExit(f"idx {start_idx} {end_idx}")

new_block = """        <Suspense
          fallback={
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="flex h-[320px] items-center justify-center rounded-lg border border-gray-200 bg-white">
                <div className="animate-pulse text-gray-400">
                  Cargando graficos...
                </div>
              </div>
              <div className="flex h-[320px] items-center justify-center rounded-lg border border-gray-200 bg-white">
                <div className="animate-pulse text-gray-400">
                  Cargando graficos...
                </div>
              </div>
            </div>
          }
        >
          <DashboardPagosCharts
            loadingPagosEstado={loadingPagosEstado}
            datosPagosEstado={datosPagosEstado}
            totalPagos={totalPagos}
            COLORS_ESTADO={COLORS_ESTADO}
            loadingEvolucion={loadingEvolucion}
            datosEvolucion={datosEvolucion}
          />
        </Suspense>

"""
out = "".join(lines[:start_idx] + [new_block] + lines[end_idx:])
p.write_text(out, encoding="utf-8")
print("ok", start_idx, end_idx)
