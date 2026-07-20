# -*- coding: utf-8 -*-
import os
import sys
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
        raise SystemExit("plantilla 29 no encontrada")
    cuerpo = p.cuerpo or ""
    if "{{logo_url}}" in cuerpo:
        p.cuerpo = cuerpo.replace("{{logo_url}}", "{{LOGO_URL}}")
        db.commit()
        print("OK plantilla 29: logo_url -> LOGO_URL")
    else:
        print("sin cambio; tokens:", "{{LOGO_URL}}" in cuerpo, "{{logo_url}}" in cuerpo)
    # verify
    print("img snippet:", [m for m in __import__("re").findall(r"<img[^>]+>", p.cuerpo or "", flags=__import__("re").I)])
finally:
    db.close()
