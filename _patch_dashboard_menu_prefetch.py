from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardMenu.tsx"
)
t = p.read_text(encoding="utf-8")
needle = "  const queryClient = useQueryClient()\n\n  const [filtros, setFiltros]"
insert = """  const queryClient = useQueryClient()

  useEffect(() => {
    const run = async () => {
      try {
        await queryClient.prefetchQuery({
          queryKey: ['dashboard-pagos-inicial', {}],
          queryFn: async () =>
            apiClient.get('/api/v1/dashboard/pagos-inicial?meses_evolucion=6'),
          staleTime: 2 * 60 * 1000,
        })
      } catch {
        /* prefetch opcional */
      }
      try {
        await queryClient.prefetchQuery({
          queryKey: ['dashboard-financiamiento-inicial', {}],
          queryFn: async () =>
            apiClient.get(
              '/api/v1/dashboard/financiamiento-inicial?meses_tendencia=12'
            ),
          staleTime: 2 * 60 * 1000,
        })
      } catch {
        /* prefetch opcional */
      }
    }
    void run()
  }, [queryClient])

  const [filtros, setFiltros]"""
if needle not in t:
    raise SystemExit("needle not found")
t = t.replace(needle, insert, 1)
p.write_text(t, encoding="utf-8")
print("ok")
