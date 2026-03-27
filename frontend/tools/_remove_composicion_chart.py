"""Remove composicion-morosidad chart from DashboardMenu.tsx (one-shot)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "DashboardMenu.tsx"
t = p.read_text(encoding="utf-8")

t = t.replace(
    "  FinanciamientoPorRangosResponse,\n  ComposicionMorosidadResponse,\n  CobranzasSemanalesResponse,",
    "  FinanciamientoPorRangosResponse,\n  CobranzasSemanalesResponse,",
)

block1 = """  const periodoComposicionMorosidad = getPeriodoGrafico('composicion-morosidad')

  const {
    data: datosComposicionMorosidad,
    isLoading: loadingComposicionMorosidad,
  } = useQuery({
    queryKey: [
      'composicion-morosidad',
      periodoComposicionMorosidad,
      JSON.stringify(filtros),
    ],

    queryFn: async () => {
      const params = construirFiltrosObject(periodoComposicionMorosidad)

      const queryParams = new URLSearchParams()

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      const response = await apiClient.get(
        `/api/v1/dashboard/composicion-morosidad?${queryParams.toString()}`
      )

      return response as ComposicionMorosidadResponse
    },

    staleTime: 4 * 60 * 60 * 1000,

    refetchOnWindowFocus: false,

    enabled: true,
  })

"""

if block1 not in t:
    raise SystemExit("block1 (useQuery composicion) missing")
t = t.replace(block1, "", 1)

inv = """      await queryClient.invalidateQueries({
        queryKey: ['composicion-morosidad'],
        exact: false,
      })

"""
if inv not in t:
    raise SystemExit("invalidate composicion missing")
t = t.replace(inv, "", 1)

ref = """      await queryClient.refetchQueries({
        queryKey: ['composicion-morosidad'],
        exact: false,
      })

"""
if ref not in t:
    raise SystemExit("refetch composicion missing")
t = t.replace(ref, "", 1)

color = """  const colorComposicionBarra = (categoria: string) => {
    const c = String(categoria ?? '')
    if (c === 'Pagado') return '#15803d'
    if (c === 'Pendiente') return '#2563eb'
    if (c === 'Pendiente parcial') return '#ca8a04'
    if (c === 'Vencido') return '#ea580c'
    if (c === 'Mora (4 meses+)') return '#7f1d1d'
    return '#64748b'
  }

"""
if color not in t:
    raise SystemExit("colorComposicionBarra missing")
t = t.replace(color, "", 1)

# Remove motion.div block containing "Préstamos por estado de la última cuota"
card_start = "          <motion.div\n            initial={{ opacity: 0, y: 20 }}\n            animate={{ opacity: 1, y: 0 }}\n            transition={{ delay: 0.82 }}\n            className=\"h-full\"\n          >\n            <Card className=\"flex h-full flex-col overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg\">\n              <CardHeader className=\"border-b border-gray-200/80 bg-gradient-to-r from-rose-50/90 to-red-50/90 pb-3\">"

idx = t.find(card_start)
if idx == -1:
    raise SystemExit("card block start not found")
# Must be the composicion card: check title follows
if "Préstamos por estado de la última cuota" not in t[idx : idx + 800]:
    raise SystemExit("wrong card block (title mismatch)")

# Find end: </motion.div> after this card's closing - first occurrence after idx of
# closing pattern for this card
sub = t[idx:]
end_marker = "          </motion.div>\n        </div>\n\n        {/* GR"
end_pos = sub.find(end_marker)
if end_pos == -1:
    raise SystemExit("card block end not found")
removed = sub[:end_pos]
# Verify removed section contains composicion
if "composicion-morosidad" not in removed:
    raise SystemExit("sanity: composicion not in removed block")
new_t = t[:idx] + sub[end_pos:]
t = new_t

p.write_text(t, encoding="utf-8")
print("ok", p)
