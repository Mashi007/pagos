"""Diagnostico completo: por que V27974365 no aparece en cola Cobros."""
import os
import sys
from datetime import date, timedelta

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)

env_path = os.path.join(REPO, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import text, select
from app.core.database import SessionLocal
from app.models.pago_reportado import PagoReportado
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.api.v1.endpoints.cobros.routes import (
    _list_pagos_reportados_payload,
    _kpis_pagos_reportados_payload,
    _item_falla_validadores_cola_manual,
    _pago_reportado_list_items_from_rows,
    _invalidate_cobros_listado_kpis_cache,
)

CED = "V27974365"
hoy = date.today()
desde = hoy - timedelta(days=90)

db = SessionLocal()
print("=== REPORTES CEDULA 27974365 ===")
rows = db.execute(
    text(
        "SELECT id, estado, falla_validadores_manual, gemini_coincide_exacto, "
        "referencia_interna, created_at, canal_ingreso "
        "FROM pagos_reportados "
        "WHERE UPPER(CONCAT(COALESCE(tipo_cedula,''), COALESCE(numero_cedula,''))) "
        "LIKE '%27974365%' ORDER BY id DESC"
    )
).fetchall()
for r in rows:
    exp = db.execute(
        select(PagoReportadoExportado).where(
            PagoReportadoExportado.pago_reportado_id == r[0]
        )
    ).scalars().first()
    print(r, "EXPORTADO=" + str(bool(exp)))

print("\n=== LISTADO API (filtros UI: 90d + cedula) ===")
for estado in (None, "en_revision", ""):
    est = None if estado in (None, "") else estado
    payload = _list_pagos_reportados_payload(
        db,
        estado=est,
        fecha_desde=desde,
        fecha_hasta=hoy,
        cedula=CED,
        institucion=None,
        page=1,
        per_page=20,
    )
    ids = [it.id for it in payload["items"]]
    print(f"estado={est!r} total={payload['total']} ids={ids}")

print("\n=== KPIs ===")
kpis = _kpis_pagos_reportados_payload(
    db,
    fecha_desde=desde,
    fecha_hasta=hoy,
    cedula=CED,
    institucion=None,
)
print(kpis)

pr = db.execute(select(PagoReportado).where(PagoReportado.id == 9811)).scalars().first()
if pr:
    it = _pago_reportado_list_items_from_rows(db, [pr])[0]
    print("\n9811 item estado=", it.estado, "falla_cola=", _item_falla_validadores_cola_manual(it))

try:
    _invalidate_cobros_listado_kpis_cache()
    print("\nCache Redis/memoria invalidada.")
except Exception as e:
    print("\nCache invalidate error:", e)

db.close()
