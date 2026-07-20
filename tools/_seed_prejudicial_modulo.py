# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
env_path = ROOT / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from app.core.database import SessionLocal
from app.services.notificacion_plantilla_prejudicial import asegurar_modulo_prejudicial

db = SessionLocal()
try:
    info = asegurar_modulo_prejudicial(db, forzar_contenido_plantilla=True)
    db.commit()
    print(info)
finally:
    db.close()
