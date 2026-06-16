"""Simula listado con filtros de fecha como el frontend (90 dias)."""
import os
import sys
from datetime import date, datetime, timedelta

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

from sqlalchemy import text
from app.core.database import SessionLocal
from app.api.v1.endpoints.cobros.routes import _list_pagos_reportados_payload

db = SessionLocal()
hoy = date.today()
desde = hoy - timedelta(days=90)
print("FECHAS:", desde, hoy)
print("ROW:", db.execute(text("SELECT id,estado,created_at FROM pagos_reportados WHERE id=9811")).fetchone())

for estado in ("", "en_revision"):
    r = _list_pagos_reportados_payload(
        db,
        estado=estado or None,
        fecha_desde=desde,
        fecha_hasta=hoy,
        cedula="V27974365",
        institucion=None,
        page=1,
        per_page=20,
    )
    print(f"estado={estado!r} total={r['total']} ids={[it.id for it in r['items']]}")
db.close()
