from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardPagos.tsx"
)
t = p.read_text(encoding="utf-8")
start = "        {/* GRA"
end = "        {/* BOTONES EXPLORAR DETALLES */}"
i0 = t.find(start)
i1 = t.find(end)
if i0 < 0 or i1 < 0 or i1 <= i0:
    raise SystemExit(f"markers not found {i0} {i1}")

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

t = t[:i0] + new_block + t[i1:]
p.write_text(t, encoding="utf-8")
print("replaced charts block")
