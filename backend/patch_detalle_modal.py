from pathlib import Path

path = Path(__file__).resolve().parent.parent / "frontend/src/components/prestamos/PrestamoDetalleModal.tsx"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

start = None
end = None
for i, line in enumerate(lines):
    if "{/* Orden" in line and "fecha_base_calculo" in line and "como base" in line:
        start = i
        break
if start is None:
    raise SystemExit("start not found")
for j in range(start, len(lines)):
    if lines[j].strip() == "})()}":
        end = j
        break
if end is None:
    raise SystemExit("end not found")

new_block_lines = [
    '                    <div className="min-w-0">\n',
    '                      <label className="text-sm text-gray-600">Fecha de Aprobación</label>\n',
    "                      <p className=\"font-medium\">\n",
    "                        {prestamoData.fecha_aprobacion ? formatDate(prestamoData.fecha_aprobacion) : '-'}\n",
    "                      </p>\n",
    '                      <p className="text-xs text-gray-500 mt-0.5">Base para vencimientos de la tabla de amortización</p>\n',
    "                    </div>\n",
]

out = lines[:start] + new_block_lines + lines[end + 1 :]
path.write_text("".join(out), encoding="utf-8")
print("ok", start + 1, end + 1)
