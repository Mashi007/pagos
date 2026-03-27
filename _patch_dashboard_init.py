from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\dashboard\__init__.py"
)
t = p.read_text(encoding="utf-8")
t = t.replace(
    "from . import graficos, kpis",
    "from . import financiamiento_inicial, graficos, kpis, pagos_inicial",
)
old = 'router.include_router(graficos.router, tags=["dashboard-graficos"])'
new = '''router.include_router(graficos.router, tags=["dashboard-graficos"])
router.include_router(pagos_inicial.router, tags=["dashboard-pagos-inicial"])
router.include_router(financiamiento_inicial.router, tags=["dashboard-financiamiento-inicial"])'''
if old not in t:
    raise SystemExit("pattern not found")
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("ok")
