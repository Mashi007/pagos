"""Fix broken nested ternary in CobrosPagosReportadosPage.tsx."""
from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "src" / "pages" / "CobrosPagosReportadosPage.tsx"
t = p.read_text(encoding="utf-8")
old = ") : !data?.items?.length ? (<p className=\"text-gray-500\">No hay registros.</p>)"
new = (
    ") : !data?.items?.length ? (\n"
    "            <p className=\"text-gray-500\">No hay registros.</p>\n"
    "          ) : ("
)
if old not in t:
    raise SystemExit("pattern not found")
# Remove the duplicate ") : (" that follows the blank lines after old block
t = t.replace(old, new, 1)
# Collapse duplicate ") : (" if present right after replacement
t = re.sub(
    r"\) : \(\s+\) : \(",
    ") : (",
    t,
    count=1,
)
p.write_text(t, encoding="utf-8")
print("patched")
