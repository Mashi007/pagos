# -*- coding: utf-8 -*-
"""Patch pagos.py: use DatosImportadosConErrores in import, add total_datos_revisar and endpoints."""
import re

path = "app/api/v1/endpoints/pagos.py"  # from backend/
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Add import
if "DatosImportadosConErrores" not in c:
    c = c.replace(
        "from app.models.pago_reportado import PagoReportado",
        "from app.models.pago_reportado import PagoReportado\nfrom app.models.datos_importados_conerrores import DatosImportadosConErrores",
    )

# 2) In import function: replace PagoConError with DatosImportadosConErrores and add referencia_interna
start = c.find("ORIGEN_COBROS_REPORTADOS = ")
end = c.find('@router.post("/validar-filas-batch"')
if start == -1 or end == -1:
    raise SystemExit("Markers not found")
section = c[start:end]
section = section.replace("PagoConError(", "DatosImportadosConErrores(")
# Add referencia_interna before fila_origen where we have observaciones=ORIGEN_COBROS_REPORTADOS
section = re.sub(
    r"(observaciones=ORIGEN_COBROS_REPORTADOS,)\s*\n(\s*fila_origen=pr\.id)",
    r"\1\n                referencia_interna=(pr.referencia_interna or \"\")[:100] or None,\n                \2",
    section,
)
c = c[:start] + section + c[end:]

# 3) Add total_datos_revisar after db.commit() in import and update return
old_return = """    db.commit()
    return {
        "registros_procesados": registros_procesados,
        "registros_con_error": len(ids_pagos_con_errores),
        "errores_detalle": errores_detalle[:100],
        "ids_pagos_con_errores": ids_pagos_con_errores,
        "cuotas_aplicadas": cuotas_aplicadas,
        "mensaje": f"Importados {registros_procesados} pagos desde Cobros; {len(ids_pagos_con_errores)} con error (Revisar Pagos).",
    }"""
new_return = """    db.commit()
    total_datos_revisar = db.execute(select(func.count()).select_from(DatosImportadosConErrores)).scalar() or 0
    return {
        "registros_procesados": registros_procesados,
        "registros_con_error": len(ids_pagos_con_errores),
        "errores_detalle": errores_detalle[:100],
        "ids_pagos_con_errores": ids_pagos_con_errores,
        "cuotas_aplicadas": cuotas_aplicadas,
        "total_datos_revisar": total_datos_revisar,
        "mensaje": f"Importados {registros_procesados} pagos desde Cobros; {len(ids_pagos_con_errores)} con error (revisar: descargar Excel).",
    }"""
if old_return not in c:
    raise SystemExit("Return block not found")
c = c.replace(old_return, new_return, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: import uses DatosImportadosConErrores and return has total_datos_revisar.")
