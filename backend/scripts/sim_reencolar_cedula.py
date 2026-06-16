"""Simula busqueda con reencolado automatico de infopagos aprobado."""
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

from sqlalchemy import text
from app.core.database import SessionLocal
from app.api.v1.endpoints.cobros.routes import _list_pagos_reportados_payload

CED = "V27974365"
hoy = date.today()
desde = hoy - timedelta(days=90)
db = SessionLocal()

# simular aprobado auto
db.execute(
    text(
        "UPDATE pagos_reportados SET estado='aprobado', falla_validadores_manual=false, "
        "usuario_gestion_id=NULL WHERE id=9811"
    )
)
db.commit()
print("ANTES listado:", db.execute(text("SELECT id,estado FROM pagos_reportados WHERE id=9811")).fetchone())

r = _list_pagos_reportados_payload(
    db,
    estado=None,
    fecha_desde=desde,
    fecha_hasta=hoy,
    cedula=CED,
    institucion=None,
    page=1,
    per_page=20,
)
print("LISTADO total=", r["total"], "ids=", [x.id for x in r["items"]])
print("DESPUES:", db.execute(text("SELECT id,estado FROM pagos_reportados WHERE id=9811")).fetchone())
db.close()
