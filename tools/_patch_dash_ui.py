from pathlib import Path

p = Path("frontend/src/pages/DashboardMenu.tsx")
t = p.read_text(encoding="utf-8")

marker = "datosComposicionMorosidad?.puntos?.length"
idx = t.find(marker)
if idx < 0:
    raise SystemExit("composicion chart not found")

chunk = t[:idx]
p_start = chunk.rfind('<p className="mt-1 text-xs text-gray-600">')
if p_start < 0:
    raise SystemExit("p tag not found")
p_end = chunk.find("</p>", p_start) + len("</p>")
old_p = t[p_start:p_end]

if "Cada préstamo" not in old_p:
    raise SystemExit(f"unexpected paragraph: {old_p[:200]!r}")

new_p = """<p className="mt-1 text-xs text-gray-600">
                  Incluye préstamos al día (sin cuotas vencidas sin pagar). Si hay
                  atraso, cada préstamo cuenta una sola vez según su mayor atraso.
                  1-30, 31-60 y 61-89 días = Vencido; 90+ días = Moroso (snapshot al
                  día de hoy).
                </p>"""

t = t[:p_start] + new_p + t[p_end:]

idx = t.find(marker)
sub = t[idx : idx + 3500]
bar_idx = sub.find('dataKey="cantidad_prestamos"')
if bar_idx < 0:
    raise SystemExit("Bar cantidad_prestamos not found")
bar_start_rel = sub.rfind("<Bar", 0, bar_idx)
bar_end_rel = sub.find("/>", bar_idx) + 2
old_b = sub[bar_start_rel:bar_end_rel]

new_b = """<Bar
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

if old_b not in t:
    raise SystemExit("old Bar block not found:\n" + repr(old_b[:200]))

t = t.replace(old_b, new_b, 1)
p.write_text(t, encoding="utf-8")
print("ok")
