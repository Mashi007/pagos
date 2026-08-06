from app.core.database import SessionLocal
from app.api.v1.endpoints.cobros.reportados_listado_payload import (
  _list_pagos_reportados_payload,
  _kpis_pagos_reportados_payload,
  _clamp_fechas_listado_cobros,
)
print("clamp none", _clamp_fechas_listado_cobros(None, None))
db=SessionLocal()
try:
  lista = _list_pagos_reportados_payload(
    db, page=1, per_page=20, estado="en_revision",
    incluir_exportados=False, fecha_desde=None, fecha_hasta=None,
    cedula=None, institucion=None, emit_manual_estado_counts_for_kpis=False,
  )
  print("en_revision total", lista.get("total"), "page_items", len(lista.get("items") or []))
  lista2 = _list_pagos_reportados_payload(
    db, page=1, per_page=20, estado=None,
    incluir_exportados=False, fecha_desde=None, fecha_hasta=None,
    cedula=None, institucion=None, emit_manual_estado_counts_for_kpis=True,
  )
  print("por_gestionar total", lista2.get("total"), "manual", lista2.get("_manual_kpi_counts"))
  kpis = _kpis_pagos_reportados_payload(
    db, incluir_exportados=False, fecha_desde=None, fecha_hasta=None,
    cedula=None, institucion=None, manual_queue_counts=lista2.get("_manual_kpi_counts"),
  )
  print("kpis", {k: kpis[k] for k in ("pendiente","en_revision","rechazado","importado","total")})
finally:
  db.close()