"""Actualiza reporte 9811 (V27974365) para cola revision manual en Cobros."""
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

from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
row = db.execute(
    text(
        "SELECT id, estado, falla_validadores_manual, gemini_coincide_exacto, observacion "
        "FROM pagos_reportados WHERE id = 9811"
    )
).fetchone()
print("ANTES:", row)
if row:
    db.execute(
        text(
            "UPDATE pagos_reportados SET "
            "estado = 'en_revision', "
            "falla_validadores_manual = true "
            "WHERE id = 9811"
        )
    )
    db.commit()
    row2 = db.execute(
        text(
            "SELECT id, estado, falla_validadores_manual, gemini_coincide_exacto, observacion "
            "FROM pagos_reportados WHERE id = 9811"
        )
    ).fetchone()
    print("DESPUES:", row2)
db.close()
