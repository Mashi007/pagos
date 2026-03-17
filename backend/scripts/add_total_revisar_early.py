path = "app/api/v1/endpoints/pagos.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
old = '"ids_pagos_con_errores": [],\n            "mensaje": "No hay pagos reportados aprobados para importar."'
new = '"ids_pagos_con_errores": [],\n            "total_datos_revisar": 0,\n            "mensaje": "No hay pagos reportados aprobados para importar."'
if old not in c:
    raise SystemExit("early return block not found")
c = c.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK")
