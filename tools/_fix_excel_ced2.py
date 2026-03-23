import re
from pathlib import Path
p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\pagos.py")
t = p.read_text(encoding="utf-8")
pat = (
    r"(Autoconciliar: pagos creados por carga Excel[^\n]*\n\n"
    r"\s*ahora_up = datetime\.now\(ZoneInfo\(TZ_NEGOCIO\)\)\n\n"
    r"\s*p = Pago\(\n\n"
    r"\s*)cedula_cliente=cedula_fk,"
)
repl = r"\1cedula_cliente=cedula.strip().upper() if cedula else \"\","
t2, n = re.subn(pat, repl, t, count=1)
print("n", n)
if n != 1:
    raise SystemExit("bad n")
p.write_text(t2, encoding="utf-8", newline="\n")
print("OK")
