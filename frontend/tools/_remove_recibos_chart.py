"""Remove Recibos en bolivares chart from DashboardMenu.tsx."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "DashboardMenu.tsx"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
text = "".join(lines)

# 1) Remove type import
text = text.replace(
    "  TendenciaProgramadoTotalCobradoResponse,\n  RecibosPagosMensualUsdResponse,\n  EvolucionMensualItem,",
    "  TendenciaProgramadoTotalCobradoResponse,\n  EvolucionMensualItem,",
)

# 2) Remove useQuery block for recibos
block_q = """  const periodoRecibosUsd = getPeriodoGrafico('recibos-pagos-usd')

  const {
    data: datosRecibosUsd,
    isLoading: loadingRecibosUsd,
    isError: errorRecibosUsd,
    refetch: refetchRecibosUsd,
  } = useQuery({
    queryKey: [
      'recibos-pagos-mensual-usd',
      periodoRecibosUsd,
      JSON.stringify(filtros),
    ],

    queryFn: async () => {
      const params = construirFiltrosObject(periodoRecibosUsd)

      const queryParams = new URLSearchParams()

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      if (!queryParams.has('periodo') && periodoRecibosUsd)
        queryParams.append('periodo', periodoRecibosUsd)

      const response = await apiClient.get(
        `/api/v1/dashboard/recibos-pagos-mensual-usd${queryParams.toString() ? `?${queryParams.toString()}` : ''}`,
        { timeout: 60000 }
      )

      const r = response as RecibosPagosMensualUsdResponse

      return {
        ...r,
        estadistica: r.estadistica ?? {
          total_bs_en_usd: 0,
          total_reportes: 0,
          promedio_mensual_usd: 0,
          meses_con_datos: 0,
          primer_mes: null,
          ultimo_mes: null,
        },
      }
    },

    staleTime: 4 * 60 * 60 * 1000,

    refetchOnWindowFocus: false,

    enabled: true,
  })

"""
if block_q not in text:
    raise SystemExit("useQuery block not found")
text = text.replace(block_q, "", 1)

# 3) invalidate / refetch
inv = """      await queryClient.invalidateQueries({
        queryKey: ['recibos-pagos-mensual-usd'],
        exact: false,
      })

"""
if inv not in text:
    raise SystemExit("invalidate recibos not found")
text = text.replace(inv, "", 1)

ref = """      await queryClient.refetchQueries({
        queryKey: ['recibos-pagos-mensual-usd'],
        exact: false,
      })

"""
if ref not in text:
    raise SystemExit("refetch recibos not found")
text = text.replace(ref, "", 1)

# 4) Remove JSX: from comment through closing motion.div before Monto programado
start_marker = "            {/* Recibos solo en Bs.: USD equivalente por mes + estadística */}\n\n"
end_marker = (
    "            {/* Monto programado por día: hoy hasta una semana después */}\n\n"
)
# Try UTF-8 file may have different dash in comment - find by motion.div pattern
idx = text.find("            {/* Recibos solo en Bs.:")
if idx == -1:
    # fallback: search for Recibos en bol
    idx = text.find("<span>Recibos en bol")
    if idx == -1:
        raise SystemExit("start not found")
    # walk back to comment
    idx = text.rfind("            {/*", 0, idx)
    if idx == -1:
        raise SystemExit("comment start not found")

idx_end = text.find(
    "            {/* Monto programado por día: hoy hasta una semana después */}"
)
if idx_end == -1:
    idx_end = text.find("            {/* Monto programado por día:")
if idx_end == -1:
    raise SystemExit("end marker not found")

removed = text[idx:idx_end]
if "recibos-pagos-usd" not in removed and "datosRecibosUsd" not in removed:
    raise SystemExit("sanity: unexpected removed region")

text = text[:idx] + text[idx_end:]

p.write_text(text, encoding="utf-8")
print("ok", p)
