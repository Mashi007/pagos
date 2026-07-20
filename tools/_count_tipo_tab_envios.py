# -*- coding: utf-8 -*-
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.envio_notificacion import EnvioNotificacion

db = SessionLocal()
try:
    rows = db.execute(
        select(EnvioNotificacion.tipo_tab, func.count())
        .group_by(EnvioNotificacion.tipo_tab)
        .order_by(func.count().desc())
    ).all()
    for t, c in rows:
        print(repr(t), c)
finally:
    db.close()
