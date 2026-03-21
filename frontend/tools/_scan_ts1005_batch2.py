# Temporary: inspect files for TS1005 fixes
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"

# LoginForm: lines with ? that might be broken (exclude ?. and ?? and ?:)
path = ROOT / "components/auth/LoginForm.tsx"
text = path.read_text(encoding="utf-8")
lines = text.splitlines()
for i, line in enumerate(lines, 1):
    if "?" not in line:
        continue
    if "??" in line or "?." in line or "?:" in line:
        continue
    if re.search(r"\?\s*['\"`]", line) or re.search(r"\?\s*\w", line):
        if i >= 1500 and i <= 1600:
            print("LoginForm", i, line.strip()[:150])

# ErroresDetallados header row if any
p2 = ROOT / "components/carga-masiva/ErroresDetallados.tsx"
t2 = p2.read_text(encoding="utf-8")
for m in re.finditer(r"C[eé]dula|Nombre|Fecha|Tel", t2[:8000]):
    pass
# print slice around return [
idx = t2.find("return [")
print("ErroresDetallados return [ at", t2[: idx + 1].count("\n"))
