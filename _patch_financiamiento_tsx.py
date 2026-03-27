from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardFinanciamiento.tsx"
)
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

# imports
t = "".join(lines)
if "useQueryClient" not in t:
    t = t.replace(
        "import { useQuery } from '@tanstack/react-query'",
        "import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'",
        1,
    )

lines = t.splitlines(keepends=True)

start_idx = None
end_idx = None
for i, l in enumerate(lines):
    if l.strip().startswith("// Cargar opciones de filtros"):
        start_idx = i
    if l.strip().startswith("const [isRefreshing"):
        end_idx = i
        break
if start_idx is None or end_idx is None:
    raise SystemExit(f"range {start_idx} {end_idx}")

new_block = """  const queryClient = useQueryClient()

  const {
    data: inicialFin,
    isLoading: loadingInicialFin,
    refetch,
  } = useQuery({
    queryKey: ['dashboard-financiamiento-inicial', filtros],

    queryFn: async ({ signal }) => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses_tendencia', '12')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const res = (await apiClient.get(
        `/api/v1/dashboard/financiamiento-inicial?${queryParams.toString()}`,
        { signal }
      )) as {
        opciones_filtros: {
          analistas: string[]
          concesionarios: string[]
          modelos: string[]
        }
        kpis_dashboard: KPIsData & {
          total_prestamos?: number
          promedio_financiamiento?: number
        }
        tendencia_mensual_meses: TendenciaMensualData[]
      }

      queryClient.setQueryData(['opciones-filtros'], res.opciones_filtros)
      return res
    },

    placeholderData: keepPreviousData,

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: false,
  })

  const opcionesFiltros = inicialFin?.opciones_filtros

  const loadingOpcionesFiltros = loadingInicialFin

  const errorOpcionesFiltros = false

  const kpisRaw = inicialFin?.kpis_dashboard

  const kpisData = kpisRaw
    ? (() => {
        const total_financiamientos = kpisRaw.total_prestamos || 0
        const monto_total = kpisRaw.total_financiamiento || 0
        const monto_promedio =
          total_financiamientos > 0 ? monto_total / total_financiamientos : 0
        return {
          total_financiamiento: monto_total,
          total_financiamiento_activo: kpisRaw.total_financiamiento_activo || 0,
          total_financiamiento_inactivo:
            kpisRaw.total_financiamiento_inactivo || 0,
          total_financiamiento_finalizado:
            kpisRaw.total_financiamiento_finalizado || 0,
          total_financiamientos: total_financiamientos,
          monto_promedio,
        } as KPIsData
      })()
    : undefined

  const loadingKpis = loadingInicialFin

  const datosEstado: EstadoData[] | undefined = kpisRaw
    ? (() => {
        const total = kpisRaw.total_financiamiento || 0
        const activo = kpisRaw.total_financiamiento_activo || 0
        const inactivo = kpisRaw.total_financiamiento_inactivo || 0
        const finalizado = kpisRaw.total_financiamiento_finalizado || 0
        return [
          {
            estado: 'Activo',
            monto: activo,
            cantidad: 0,
            porcentaje: total > 0 ? (activo / total) * 100 : 0,
          },
          {
            estado: 'Inactivo',
            monto: inactivo,
            cantidad: 0,
            porcentaje: total > 0 ? (inactivo / total) * 100 : 0,
          },
          {
            estado: 'Finalizado',
            monto: finalizado,
            cantidad: 0,
            porcentaje: total > 0 ? (finalizado / total) * 100 : 0,
          },
        ]
      })()
    : undefined

  const loadingEstado = loadingInicialFin

  const datosTendencia = inicialFin?.tendencia_mensual_meses

  const loadingTendencia = loadingInicialFin

"""

out = "".join(lines[:start_idx] + [new_block] + lines[end_idx:])
p.write_text(out, encoding="utf-8")
print("ok", start_idx, end_idx)
