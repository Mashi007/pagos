from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardFinanciamiento.tsx"
)
t = p.read_text(encoding="utf-8")
needle = "  const loadingTendencia = loadingInicialFin\n\n  const [isRefreshing"
insert = r"""  const loadingTendencia = loadingInicialFin

  const { data: datosConcesionarios, isLoading: loadingConcesionarios } =
    useQuery({
      queryKey: ['prestamos-por-concesionario', filtros],

      queryFn: async () => {
        const params = construirFiltrosObject()

        const queryParams = new URLSearchParams()

        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value.toString())
        })

        const queryString = queryParams.toString()

        const response = (await apiClient.get(
          `/api/v1/dashboard/prestamos-por-concesionario${queryString ? '?' + queryString : ''}`
        )) as { concesionarios: ConcesionarioData[] }

        const top10 = response.concesionarios.slice(0, 10)

        const otros = response.concesionarios.slice(10)

        const otrosSum = otros.reduce(
          (acc, c) => ({
            cantidad_prestamos: acc.cantidad_prestamos + c.cantidad_prestamos,

            monto_total: acc.monto_total + c.monto_total,

            porcentaje_cantidad:
              acc.porcentaje_cantidad + c.porcentaje_cantidad,

            porcentaje_monto: acc.porcentaje_monto + c.porcentaje_monto,
          }),

          {
            cantidad_prestamos: 0,

            monto_total: 0,

            porcentaje_cantidad: 0,

            porcentaje_monto: 0,
          }
        )

        const result = [...top10]

        if (otrosSum.cantidad_prestamos > 0) {
          result.push({
            concesionario: 'Otros',

            ...otrosSum,
          })
        }

        return result
      },

      staleTime: 5 * 60 * 1000,

      refetchOnWindowFocus: false,

      retry: 1,
    })

  const [isRefreshing"""
if needle not in t:
    raise SystemExit("needle not found")
t = t.replace(needle, insert, 1)
p.write_text(t, encoding="utf-8")
print("ok")
