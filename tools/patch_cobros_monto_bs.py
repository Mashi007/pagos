# -*- coding: utf-8 -*-
"""Rango monto Bs 1..10_000_000 solo si moneda BS (cedula ya validada en lista)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
t = p.read_text(encoding="utf-8")

if "MIN_MONTO_BS_REPORTAR" in t:
    print("already patched")
    raise SystemExit(0)

anchor = (
    "ERROR_BS_NO_AUTORIZADO = \"Observaci\u00f3n: Bol\u00edvares. No puede enviar pago en Bol\u00edvares; su c\u00e9dula no est\u00e1 autorizada. Use USD.\"\n"
)
# file may have mojibake instead of unicode escapes - find ERROR_BS line
idx = t.find("ERROR_BS_NO_AUTORIZADO = ")
if idx == -1:
    raise SystemExit("ERROR_BS not found")
end = t.find("\n", idx)
line = t[idx : end + 1]
insert_after = end + 1
const_block = (
    "\n"
    "# Monto en bolivares (solo cedulas en cedulas_reportar_bs): 1 a 10_000_000 Bs.\n"
    "MIN_MONTO_BS_REPORTAR = 1.0\n"
    "MAX_MONTO_BS_REPORTAR = 10_000_000.0\n"
    "\n"
)

def _helper() -> str:
    return (
        "\n\ndef _validar_monto_reporte_publico(monto: float, moneda_upper: str) -> Optional[str]:\n"
        '    """Si moneda BS, rango Bs autorizado; si USD/USDT, limite general. None = OK."""\n'
        '    if moneda_upper == "BS":\n'
        "        if monto < MIN_MONTO_BS_REPORTAR or monto > MAX_MONTO_BS_REPORTAR:\n"
        "            return (\n"
        '                f"Monto en bolivares debe estar entre "\n'
        "                f\"{MIN_MONTO_BS_REPORTAR:,.0f} y {MAX_MONTO_BS_REPORTAR:,.0f} Bs. \"\n"
        '                "(cedula autorizada para pagos en bolivares)."\n'
        "            )\n"
        "        return None\n"
        "    if monto <= 0 or monto > 999_999_999.99:\n"
        '        return "Monto no valido."\n'
        "    return None\n"
    )

# Optional import if not present
if "Optional[str]" in t and "from typing import Optional" not in t[:800]:
    pass
if "from typing import Optional" not in t[:2000]:
    # insert after first typing import line
    ti = t.find("from typing import ")
    if ti == -1:
        raise SystemExit("typing import not found")
    te = t.find("\n", ti)
    line_t = t[ti : te + 1]
    if "Optional" not in line_t:
        t = t.replace(line_t, line_t.rstrip() + ", Optional\n", 1)

t = t[:insert_after] + const_block + t[insert_after:]

# insert helper before first def _referencia or after logger - find "logger = "
li = t.find("logger = logging.getLogger")
if li == -1:
    raise SystemExit("logger not found")
# after logger block blank lines - insert before def _referencia_display
ri = t.find("\ndef _referencia_display", li)
if ri == -1:
    raise SystemExit("_referencia_display not found")
t = t[:ri] + _helper() + t[ri:]

old1 = (
    "    if monto <= 0 or monto > 999_999_999.99:\n\n"
    "        return EnviarReporteResponse(ok=False, error=\"Monto no vAlido.\")\n"
)
# try exact file content - may vary
import re

pat1 = re.compile(
    r"\n    if monto <= 0 or monto > 999_999_999\.99:\s*\n\s*\n\s*return EnviarReporteResponse\(ok=False, error=\"[^\"]+\"\)\s*\n",
    re.M,
)
m1 = pat1.search(t)
if not m1:
    raise SystemExit("pattern enviar_reporte monto not found")

rep1 = (
    "\n    err_monto = _validar_monto_reporte_publico(monto, moneda_upper)\n\n"
    "    if err_monto:\n\n"
    "        return EnviarReporteResponse(ok=False, error=err_monto)\n\n"
)
t = pat1.sub(rep1, t, count=1)

pat2 = re.compile(
    r"\n    if monto <= 0 or monto > 999_999_999\.99:\s*\n\s*\n\s*return EnviarReporteInfopagosResponse\(ok=False, error=\"[^\"]+\"\)\s*\n",
    re.M,
)
m2 = pat2.search(t)
if not m2:
    raise SystemExit("pattern infopagos monto not found")
rep2 = (
    "\n    err_monto = _validar_monto_reporte_publico(monto, moneda_upper)\n\n"
    "    if err_monto:\n\n"
    "        return EnviarReporteInfopagosResponse(ok=False, error=err_monto)\n\n"
)
t = pat2.sub(rep2, t, count=1)

p.write_text(t, encoding="utf-8")
print("ok")
