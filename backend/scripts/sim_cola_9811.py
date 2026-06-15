"""Simula si reporte 9811 entra en cola manual Cobros."""
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

from app.core.database import SessionLocal
from app.api.v1.endpoints.cobros.routes import _list_pagos_reportados_payload

db = SessionLocal()
for estado in (None, "en_revision", "pendiente"):
    r = _list_pagos_reportados_payload(
        db,
        estado=estado,
        fecha_desde=None,
        fecha_hasta=None,
        cedula="V27974365",
        institucion=None,
        page=1,
        per_page=50,
    )
    ids = [it.id for it in r["items"]]
    print(f"estado={estado!r} total={r['total']} ids={ids}")
db.close()
