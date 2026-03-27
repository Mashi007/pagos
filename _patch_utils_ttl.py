from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\dashboard\utils.py"
)
t = p.read_text(encoding="utf-8")
t = t.replace("_OPCIONES_FILTROS_TTL_SEC = 300", "_OPCIONES_FILTROS_TTL_SEC = 360", 1)
t = t.replace("_PRESTAMOS_GRAFICOS_CACHE_TTL_SEC = 300", "_PRESTAMOS_GRAFICOS_CACHE_TTL_SEC = 360", 1)
p.write_text(t, encoding="utf-8")
print("ok")
