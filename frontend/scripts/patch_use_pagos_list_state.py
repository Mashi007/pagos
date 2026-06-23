"""Move PagosList logic into usePagosListState hook."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "components" / "pagos"
MAIN = ROOT / "PagosList.tsx"
HOOK = ROOT / "pagosList" / "usePagosListState.ts"

text = MAIN.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

fn_start = next(i for i, l in enumerate(lines) if "export function PagosList()" in l)
body_start = fn_start + 1
ret_line = next(
    i
    for i, l in enumerate(lines)
    if i > body_start and l.strip() == "return ("
)
body = "".join(lines[body_start:ret_line])

# symbols to return: const x =, function handlers, useX hooks results
symbols = []
for m in re.finditer(r"^  const (\w+) =", body, re.M):
    symbols.append(m.group(1))
for m in re.finditer(r"^  const \{([^}]+)\}", body, re.M):
    for part in m.group(1).split(","):
        name = part.strip().split(":")[0].strip()
        if name:
            symbols.append(name)
for m in re.finditer(r"^  const (\w+) = use", body, re.M):
    pass  # already captured

symbols = list(dict.fromkeys(symbols))  # unique preserve order

imports = text[:fn_start]

hook = (
    imports.replace("export function PagosList()", "", 1)
    + "\nexport function usePagosListState() {\n"
    + body
    + "\n  return {\n"
    + ",\n".join(f"    {s}" for s in symbols)
    + ",\n  }\n}\n"
)

HOOK.write_text(hook, encoding="utf-8")

new_main = (
    imports
    + "import { usePagosListState } from './pagosList/usePagosListState'\n\n"
    + "export function PagosList() {\n"
    + "  const state = usePagosListState()\n"
    + "".join(lines[ret_line:])
)

# replace identifiers in JSX with state.x - too hard

# instead destructure in PagosList
destructure = "  const {\n" + ",\n".join(f"    {s}" for s in symbols) + ",\n  } = state\n\n"
new_main = (
    imports
    + "import { usePagosListState } from './pagosList/usePagosListState'\n\n"
    + "export function PagosList() {\n"
    + "  const state = usePagosListState()\n"
    + destructure
    + "".join(lines[ret_line:])
)

MAIN.write_text(new_main, encoding="utf-8")
print("hook symbols:", len(symbols), "body lines:", body.count("\n"))
