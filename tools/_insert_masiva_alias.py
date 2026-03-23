from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
t = p.read_text(encoding="utf-8")
needle = (
    '        "mensaje": f"Cascada masiva: {len(ok)} ok, {len(errores)} error(es).",\n'
    "    }\n\nclass ConciliarAmortizacionMasivaBody"
)
repl = (
    '        "mensaje": f"Cascada masiva: {len(ok)} ok, {len(errores)} error(es).",\n'
    "    }\n\n\n"
    "# Compat: nombre de handler historico.\n"
    "reaplicar_fifo_aplicacion_masiva = reaplicar_cascada_aplicacion_masiva\n\n\n"
    "class ConciliarAmortizacionMasivaBody"
)
if needle not in t:
    raise SystemExit("needle not found")
p.write_text(t.replace(needle, repl, 1), encoding="utf-8", newline="\n")
print("OK")
