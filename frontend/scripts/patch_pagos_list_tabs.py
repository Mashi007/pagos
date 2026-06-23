"""Extract Tabs section from PagosList into PagosListTabsSection.tsx."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "components" / "pagos"
MAIN = ROOT / "PagosList.tsx"
OUT = ROOT / "pagosList" / "PagosListTabsSection.tsx"

text = MAIN.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

start = next(i for i, l in enumerate(lines) if "<Tabs value={activeTab}" in l)
end = next(i for i, l in enumerate(lines) if i > start and l.strip() == "</Tabs>")

body = "".join(lines[start : end + 1])

# identifiers used in body (heuristic)
idents = set(re.findall(r"\b([a-z][a-zA-Z0-9]*)\b", body))
keywords = {
    "div", "span", "className", "Card", "Button", "true", "false", "null", "type",
    "value", "key", "map", "filter", "String", "Number", "Boolean", "void", "async",
    "await", "return", "if", "else", "const", "let", "new", "Set", "Array", "Date",
    "Math", "parseInt", "parseFloat", "cn", "formatDate", "toast", "navigate",
}
props = sorted(x for x in idents if x not in keywords and len(x) > 2 and x[0].islower())

header = '''import type { ComponentType } from 'react'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '../../ui/tabs'
import { PagosListResumen } from '../PagosListResumen'

export type PagosListTabsSectionProps = Record<string, unknown>

export function PagosListTabsSection(props: PagosListTabsSectionProps) {
'''
# destructure all props as locals for unchanged JSX
destructure = "  const {\n"
for p in props:
    destructure += f"    {p},\n"
destructure += "  } = props\n\n  return (\n"

footer = "\n  )\n}\n"

OUT.write_text(header + destructure + body + footer, encoding="utf-8")

replacement = "        <PagosListTabsSection props={pagosListTabsProps} />\n"
# build props object in PagosList - insert before return
props_obj = "  const pagosListTabsProps: PagosListTabsSectionProps = {\n"
for p in props:
    props_obj += f"    {p},\n"
props_obj += "  }\n\n"

new_main = (
    text[:start]
    + replacement
    + "".join(lines[end + 1 :])
)

import_line = "import { useStaffComprobantePreview } from './pagosList/useStaffComprobantePreview'\n"
new_main = new_main.replace(
    import_line,
    import_line
    + "import {\n  PagosListTabsSection,\n  type PagosListTabsSectionProps,\n} from './pagosList/PagosListTabsSection'\n",
)

# insert props object before return (
ret_idx = new_main.rfind("  return (\n")
if ret_idx < 0:
    raise SystemExit("return not found")
new_main = new_main[:ret_idx] + props_obj + new_main[ret_idx:]

MAIN.write_text(new_main, encoding="utf-8")
print("props count:", len(props))
print("extracted lines:", end - start + 1)
