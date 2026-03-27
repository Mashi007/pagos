"""Patch DashboardMenu composicion chart text and colors."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "DashboardMenu.tsx"
t = p.read_text(encoding="utf-8")

old = """  const chartAxisTick = { fontSize: 13, fill: '#374151', fontWeight: 500 }

  const chartLegendStyle = {"""

ins = """  const chartAxisTick = { fontSize: 13, fill: '#374151', fontWeight: 500 }

  const colorComposicionBarra = (categoria: string) => {
    const c = String(categoria ?? '')
    if (c === 'Pagado') return '#15803d'
    if (c === 'Pendiente') return '#2563eb'
    if (c === 'Pendiente parcial') return '#ca8a04'
    if (c === 'Vencido') return '#ea580c'
    if (c === 'Mora (4 meses+)') return '#7f1d1d'
    return '#64748b'
  }

  const chartLegendStyle = {"""

if old not in t:
    raise SystemExit("insert anchor missing")
t = t.replace(old, ins, 1)

old2 = "                    <span>Cantidad de préstamos con pago vencido</span>"
new2 = "                    <span>Préstamos por estado de la última cuota</span>"
if old2 not in t:
    raise SystemExit("title anchor missing")
t = t.replace(old2, new2, 1)

old3 = """                <p className="mt-1 text-xs text-gray-600">
                  Incluye préstamos al día (sin cuotas vencidas sin pagar). Si
                  hay atraso, cada préstamo cuenta una sola vez según su mayor
                  atraso. 1-30, 31-60, 61-89 y 90-120 días = Vencido; 121+ días
                  = Moroso (snapshot al día de hoy).
                </p>"""
new3 = """                <p className="mt-1 text-xs text-gray-600">
                  Por cada préstamo aprobado se toma la última fila de la tabla
                  de amortización (mayor número de cuota) y el estado de esa
                  cuota: Pagado, Pendiente, Pendiente parcial, Vencido o Mora
                  (4+ meses desde el vencimiento). Misma regla que la amortización
                  en Caracas (hoy).
                </p>"""
if old3 not in t:
    raise SystemExit("desc anchor missing")
t = t.replace(old3, new3, 1)

old4 = """                                fill={
                                  row.categoria === 'Al día'
                                    ? '#15803d'
                                    : '#be123c'
                                }"""
new4 = """                                fill={colorComposicionBarra(
                                  String(row.categoria ?? '')
                                )}"""
if old4 not in t:
    raise SystemExit("fill anchor missing")
t = t.replace(old4, new4, 1)

p.write_text(t, encoding="utf-8")
print("ok", p)
