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

from app.core.database import SessionLocal
from app.models.plantilla_notificacion import PlantillaNotificacion

db = SessionLocal()
try:
    p = db.get(PlantillaNotificacion, 29)
    if not p:
        rows = db.query(PlantillaNotificacion).filter(PlantillaNotificacion.tipo == "PAGO_10_DIAS_ATRASADO").all()
        p = rows[0] if rows else None
    if not p:
        print("no plantilla")
    else:
        print("id", p.id, "nombre", p.nombre)
        cuerpo = p.cuerpo or ""
        print("cuerpo_len", len(cuerpo))
        # extract img tags / logo refs
        import re
        for m in re.finditer(r"<img[^>]+>", cuerpo, re.I):
            print("IMG:", m.group(0)[:500])
        for m in re.finditer(r"logo|LOGO|https?://[^\s\"']+\.(?:png|jpg|jpeg|gif|svg|webp)", cuerpo, re.I):
            print("HIT:", m.group(0)[:200])
        # show first 800 chars
        print("---HEAD---")
        print(cuerpo[:800])
finally:
    db.close()
