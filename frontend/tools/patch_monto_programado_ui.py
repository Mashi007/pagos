"""Update Monto programado por dia labels (D+4..D+7) in DashboardMenu.tsx."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "DashboardMenu.tsx"
t = p.read_text(encoding="utf-8")

repls = [
    (
        "            {/* Monto programado por día: hoy hasta una semana después */}\n",
        "            {/* Monto programado por día: ventana D+4 a D+7 (4 días en el futuro) */}\n",
    ),
    (
        "            {/* Monto programado por día: hoy hasta una semana despu\\u00E9s */}\n",
        "            {/* Monto programado por día: ventana D+4 a D+7 (4 días en el futuro) */}\n",
    ),
    (
        "                      Hoy hasta 1 semana\n",
        "                      D+4 a D+7 (4 días)\n",
    ),
    (
        "                  <CardDescription className=\"text-sm text-gray-600\">\n"
        "                    Suma de monto_cuota (cuotas con vencimiento cada día)\n"
        "                    desde hoy hasta 7 días después\n"
        "                  </CardDescription>\n",
        "                  <CardDescription className=\"text-sm text-gray-600\">\n"
        "                    Suma de monto_cuota por fecha de vencimiento entre hoy +4 y hoy +7\n"
        "                    (cuatro días corridos en el futuro).\n"
        "                  </CardDescription>\n",
    ),
    (
        "                  <CardDescription className=\"text-sm text-gray-600\">\n"
        "                    Suma de monto_cuota (cuotas con vencimiento cada d\\u00EDa)\n"
        "                    desde hoy hasta 7 d\\u00EDas despu\\u00E9s\n"
        "                  </CardDescription>\n",
        "                  <CardDescription className=\"text-sm text-gray-600\">\n"
        "                    Suma de monto_cuota por fecha de vencimiento entre hoy +4 y hoy +7\n"
        "                    (cuatro días corridos en el futuro).\n"
        "                  </CardDescription>\n",
    ),
    (
        "                      No hay datos de monto programado para los próximos 7\n"
        "                      días\n",
        "                      No hay datos de monto programado para el rango D+4 a D+7\n",
    ),
    (
        "                      No hay datos de monto programado para los próximos 7\n"
        "                      d\\u00EDas\n",
        "                      No hay datos de monto programado para el rango D+4 a D+7\n",
    ),
]

for old, new in repls:
    if old in t:
        t = t.replace(old, new, 1)

p.write_text(t, encoding="utf-8")
print("ok", p)
