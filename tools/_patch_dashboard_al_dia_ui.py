from pathlib import Path

p = Path("frontend/src/pages/DashboardMenu.tsx")
t = p.read_text(encoding="utf-8")

old_p = """                <p className=\"mt-1 text-xs text-gray-600\">
                  Cada préstamo cuenta una sola vez, en la barra según su mayor
                  atraso entre cuotas vencidas sin pagar. 1-30, 31-60 y 61-89 días =
                  Vencido; 90+ días = Moroso (snapshot al día de hoy).
                </p>"""

new_p = """                <p className=\"mt-1 text-xs text-gray-600\">
                  Incluye préstamos al día (sin cuotas vencidas sin pagar). Si hay
                  atraso, cada préstamo cuenta una sola vez según su mayor atraso.
                  1-30, 31-60 y 61-89 días = Vencido; 90+ días = Moroso (snapshot al
                  día de hoy).
                </p>"""

old_b = """                          <Bar
                            dataKey="cantidad_prestamos"
                            fill="#be123c"
                            name="Cantidad de préstamos"
                            radius={[4, 4, 0, 0]}
                          />"""

new_b = """                          <Bar
                            dataKey="cantidad_prestamos"
                            name="Cantidad de préstamos"
                            radius={[4, 4, 0, 0]}
                          >
                            {filteredData.map((row, index) => (
                              <Cell
                                key={row.categoria ?? index}
                                fill={
                                  row.categoria === 'Al día' ? '#15803d' : '#be123c'
                                }
                              />
                            ))}
                          </Bar>"""

if old_p not in t:
    raise SystemExit("subtitle block not found")
if old_b not in t:
    raise SystemExit("bar block not found")
t = t.replace(old_p, new_p).replace(old_b, new_b)
p.write_text(t, encoding="utf-8")
print("ok")
