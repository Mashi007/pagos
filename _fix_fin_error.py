from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardFinanciamiento.tsx"
)
t = p.read_text(encoding="utf-8")
t = t.replace(
    """  const {
    data: inicialFin,
    isLoading: loadingInicialFin,
    refetch,
  } = useQuery({""",
    """  const {
    data: inicialFin,
    isLoading: loadingInicialFin,
    isError: errorOpcionesFiltros,
    refetch,
  } = useQuery({""",
    1,
)
t = t.replace("  const errorOpcionesFiltros = false\n\n", "", 1)
p.write_text(t, encoding="utf-8")
print("ok")
