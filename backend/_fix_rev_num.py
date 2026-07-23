from pathlib import Path
import re

p = Path(r"C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\ReportePagoPage.tsx")
text = p.read_text(encoding="utf-8")
replacement = (
    "/** Unico por envio: evita falso duplicado en ventana anti-doble-click entre clientes distintos. */\n"
    "function cobrosRevNumOperacionUnico(): string {\n"
    "  const suf =\n"
    "    Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)\n"
    "  return ('REV-MANUAL-' + suf).slice(0, MAX_LENGTH_NUMERO_OPERACION)\n"
    "}\n\n"
)
new_text, n = re.subn(
    r"/\*\*[^\n]*nico por env[^\n]*\*/\nfunction cobrosRevNumOperacionUnico\(\): string \{.*?\n\}\n\n",
    replacement,
    text,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit(f"replace count={n}")
p.write_text(new_text, encoding="utf-8")
chunk = p.read_text(encoding="utf-8")
idx = chunk.find("function cobrosRevNumOperacionUnico")
print(chunk[idx : idx + 260])
assert "Date.now()" in chunk[idx : idx + 260]
print("FIXED_OK")
