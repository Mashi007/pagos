"""Extract Todos tab content from PagosList."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "components" / "pagos"
MAIN = ROOT / "PagosList.tsx"
OUT = ROOT / "pagosList" / "PagosTodosTab.tsx"

lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)
start = next(i for i, l in enumerate(lines) if 'TabsContent value="todos"' in l)
end = next(
    i
    for i, l in enumerate(lines)
    if i > start and l.strip() == "</TabsContent>" and "revision-global" not in "".join(lines[start:i])
)
# find correct closing - last TabsContent before revision-global ended; todos is last tab
end = len(lines) - 1
for i in range(start + 1, len(lines)):
    if lines[i].strip() == "</TabsContent>":
        end = i

body = "".join(lines[start + 1 : end])  # inner content only

OUT.write_text(
    '''/* Tab «Todos los Pagos» — props tipados en el orquestador PagosList. */
import type { PagosTodosTabProps } from './pagosTodosTabTypes'

export function PagosTodosTab(props: PagosTodosTabProps) {
  const p = props
  return (
'''
    + body
    + """
  )
}
""",
    encoding="utf-8",
)

# replace tab content
new_lines = (
    lines[: start + 1]
    + ["            <PagosTodosTab {...pagosTodosTabProps} />\n"]
    + lines[end:]
)
MAIN.write_text("".join(new_lines), encoding="utf-8")
print("todos tab inner lines:", body.count("\n"))
