"""Move Monto programado chart into same row as Bandas $400 grid."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "DashboardMenu.tsx"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

# Line numbers 1-based from prior read
# Remove 1521-1618 (inclusive): comment blank + monto motion block
start_del = 1520  # 0-based index for line 1521
end_del = 1618    # 0-based inclusive end line 1618 -> slice end 1619

monto_block = lines[start_del:end_del]
# Remove from original
lines_wo = lines[:start_del] + lines[end_del:]

# Find grid opening after removal - line numbers shifted by -(end_del-start_del)
text = "".join(lines_wo)
needle = '        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">\n'
idx = text.find(needle)
if idx == -1:
    raise SystemExit("grid not found")

# Find position after first comment inside grid
marker = "          {/* GR"
pos = text.find(marker, idx)
if pos == -1:
    raise SystemExit("bandas comment not found")

# Dedented monto: was 12 spaces base, grid children use 10 spaces for motion
monto_lines = []
for ln in monto_block:
    if ln.startswith("            "):  # 12 spaces -> 10
        monto_lines.append("          " + ln[12:])
    elif ln.startswith("\n"):
        monto_lines.append(ln)
    else:
        monto_lines.append(ln)

monto_str = "".join(monto_lines)
insert = (
    "          {datosDashboard ? (\n"
    + monto_str.rstrip("\n")
    + "\n          ) : null}\n\n"
)

new_text = text[:pos] + insert + text[pos:]
p.write_text(new_text, encoding="utf-8")
print("ok", p)
