"""Fix broken JSX after moving Monto into grid with Bandas."""
from pathlib import Path

p = Path(__file__).resolve().parents[1].parent / "frontend" / "src" / "pages" / "DashboardMenu.tsx"
text = p.read_text(encoding="utf-8")

grid_open = '        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">'
idx = text.find(grid_open)
if idx == -1:
    raise SystemExit("grid_open not found")

sub = text[idx + len(grid_open) :]
# Bandas comment (second chart in row)
needle = "          {/* GR"
bandas_pos = sub.find(needle)
if bandas_pos == -1:
    raise SystemExit("bandas comment not found")

inner = sub[:bandas_pos]
# inner is broken block ending before Bandas comment

# Extract motion+card body: from <motion.div to </motion.div> before erroneous </div>
motion_start = inner.find("<motion.div")
if motion_start == -1:
    raise SystemExit("motion not found")
# remove leading garbage: {datosDashboard ? ( and comment
body = inner[motion_start:]
# remove trailing erroneous lines after </motion.div>
end_mv = body.rfind("</motion.div>")
if end_mv == -1:
    raise SystemExit("motion close not found")
body = body[: end_mv + len("</motion.div>")]

# Add flex h-full to Card opening in body
body = body.replace(
    '<Card className="overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">',
    '<Card className="flex h-full flex-col overflow-hidden rounded-xl border border-gray-200/90 bg-white shadow-lg">',
    1,
)

clean = (
    "\n"
    "          {datosDashboard ? (\n"
    "            <>\n"
    "              {/* Monto programado por día: ventana D+4 a D+7 (4 días en el futuro) */}\n"
    "\n"
    + "              "
    + body.replace("\n", "\n              ")
    + "\n"
    "            </>\n"
    "          ) : null}\n"
    "\n"
)

new_text = text[: idx + len(grid_open)] + clean + text[idx + len(grid_open) + len(inner) :]
p.write_text(new_text, encoding="utf-8")
print("ok", len(inner), "->", len(clean))
