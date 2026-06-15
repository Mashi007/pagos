"""Diagnostico detallado reporte 9811 vs cola Cobros."""
import os
import sys

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

from sqlalchemy import select, text
from app.core.database import SessionLocal
from app.models.pago_reportado import PagoReportado
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.api.v1.endpoints.cobros.routes import (
    _pago_reportado_list_items_from_rows,
    _item_falla_validadores_cola_manual,
    _where_clauses_cola_reportados,
    _filtros_fecha_cedula_institucion_reportados,
    _get_primer_triple_cached,
    _primer_maps_scope_key,
)

db = SessionLocal()
pr = db.execute(select(PagoReportado).where(PagoReportado.id == 9811)).scalars().first()
print("ROW:", pr.id, pr.estado, pr.falla_validadores_manual, pr.gemini_coincide_exacto)
print("CEDULA:", pr.tipo_cedula, pr.numero_cedula)
print("OBS:", (pr.observacion or "")[:200])
print("CREATED:", pr.created_at)
print("NUM_OP:", pr.numero_operacion)

exp = db.execute(
    select(PagoReportadoExportado).where(PagoReportadoExportado.pago_reportado_id == 9811)
).scalars().first()
print("EXPORTADO:", bool(exp))

items = _pago_reportado_list_items_from_rows(db, [pr])
it = items[0]
print("ITEM falla_validadores_cola_manual:", _item_falla_validadores_cola_manual(it))
print("ITEM obs:", (it.observacion or "")[:200])
print("ITEM duplicado:", getattr(it, "duplicado_en_pagos", None))

exportados_subq = select(PagoReportadoExportado.pago_reportado_id)
filtros = _filtros_fecha_cedula_institucion_reportados(
    fecha_desde=None, fecha_hasta=None, cedula="V27974365", institucion=None
)
wh = _where_clauses_cola_reportados("en_revision", False, exportados_subq, filtros)
print("WH count en_revision cedula:", db.execute(select(PagoReportado).where(*wh)).scalars().all())

scope_key = _primer_maps_scope_key(
    incluir_exportados=False, fecha_desde=None, fecha_hasta=None, cedula="V27974365", institucion=None
)
primer_precalc, primer_num_op, _ = _get_primer_triple_cached(db, wh, scope_key)
num_key = (pr.numero_operacion or "").strip()
first_id = primer_num_op.get(num_key)
print("primer_num_op first_id for", num_key, ":", first_id)

# sin filtro cedula
wh2 = _where_clauses_cola_reportados("en_revision", False, exportados_subq, [])
rows2 = db.execute(select(PagoReportado).where(PagoReportado.id == 9811)).scalars().all()
items2 = _pago_reportado_list_items_from_rows(db, rows2, primer_id_por_norm_precalc=primer_precalc)
for it2 in items2:
    print("sin cedula filter - falla:", _item_falla_validadores_cola_manual(it2))

db.close()
