from pathlib import Path
p = Path("backend/app/api/v1/__init__.py")
t = p.read_text(encoding="utf-8")
old_imp = "admin_tasas_cambio, tasas_cambio_publico"
new_imp = "admin_tasas_cambio, tasas_cambio_publico, conciliacion_bancos"
first_import_line = [ln for ln in t.splitlines() if ln.startswith("from app.api.v1.endpoints import")][0]
if "conciliacion_bancos" not in first_import_line:
    if old_imp not in t:
        raise SystemExit("import anchor missing")
    t = t.replace(old_imp, new_imp, 1)
needle = (
    "api_router.include_router(\n\n"
    "    auditoria.router,\n\n"
    '    prefix="/auditoria",\n\n'
    '    tags=["auditoria"],\n\n'
    ")"
)
insert = (
    needle
    + "\n\n# Conciliacion Bancos (Auditoria): Excel banco vs numero_documento OCR\n\n"
    + "api_router.include_router(\n\n"
    + "    conciliacion_bancos.router,\n\n"
    + '    tags=["conciliacion-bancos"],\n\n'
    + ")"
)
if "conciliacion_bancos.router" not in t:
    if needle not in t:
        raise SystemExit("needle missing: " + repr(t[t.find("auditoria.router")-40:t.find("auditoria.router")+80]))
    t = t.replace(needle, insert, 1)
p.write_text(t, encoding="utf-8")
print("patched ok")