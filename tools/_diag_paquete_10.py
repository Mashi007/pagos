# -*- coding: utf-8 -*-
import json
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
from app.models.configuracion import Configuracion
from app.services.adjunto_fijo_cobranza import (
    get_adjunto_fijo_cobranza_bytes,
    get_adjuntos_fijos_por_caso,
    _get_adjuntos_por_caso_raw,
)
from app.services.notificacion_service import get_primer_item_ejemplo_paquete_prueba
from app.models.plantilla_notificacion import PlantillaNotificacion

db = SessionLocal()
try:
    raw = _get_adjuntos_por_caso_raw(db)
    for caso in ("dias_1_retraso", "dias_10_retraso", "prejudicial"):
        cfg = raw.get(caso, [])
        loaded = get_adjuntos_fijos_por_caso(db, caso)
        print(f"=== {caso} ===")
        print("config_entries=", len(cfg))
        for i, x in enumerate(cfg):
            print("  cfg", i, {k: x.get(k) for k in ("id", "nombre_archivo", "en_bd", "ruta")})
        print("loaded=", [(n, len(b)) for n, b in loaded])

    glob = get_adjunto_fijo_cobranza_bytes(db)
    print("=== GLOBAL adjunto_fijo_cobranza ===")
    if glob:
        print(glob[0], len(glob[1]))
    else:
        print("None")
    row = db.get(Configuracion, "adjunto_fijo_cobranza")
    print("global_cfg=", (row.valor[:300] if row and row.valor else None))

    item = get_primer_item_ejemplo_paquete_prueba(db, "PAGO_10_DIAS_ATRASADO")
    if item:
        print("=== item ejemplo PAGO_10 ===")
        print({k: item.get(k) for k in ("nombre", "cedula", "prestamo_id", "numero_cuota", "dias_atraso", "cuotas_atrasadas")})
    else:
        print("sin item ejemplo")

    p = db.get(PlantillaNotificacion, 29)
    if p:
        print("=== plantilla 29 ===")
        print("nombre=", p.nombre, "tipo=", p.tipo, "activa=", p.activa)
        print("asunto=", (p.asunto or "")[:80])
        print("cuerpo_len=", len(p.cuerpo or ""))
finally:
    db.close()
