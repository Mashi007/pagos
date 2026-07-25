# -*- coding: utf-8 -*-
"""Auditoria: ningun LIQUIDADO/DESISTIMIENTO en listados de notificacion."""
import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")
for linea in io.open(".env", encoding="utf-8"):
    linea = linea.strip()
    if not linea or linea.startswith("#") or "=" not in linea:
        continue
    k, v = linea.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente
from app.services.notificacion_service import hoy_negocio, build_cuotas_pendiente_2_dias_antes_items
from app.services.notificaciones_listados_motor import build_items_retraso_uno_y_diez_dias
from app.api.v1.endpoints.notificaciones.routes import build_prejudicial_items
from app.services.notificaciones_exclusion_desistimiento import (
    item_bloqueado_para_envio_notificacion,
    cliente_tiene_prestamo_desistimiento,
    cliente_sin_cartera_activa_notif,
)

db = SessionLocal()
try:
    hoy = hoy_negocio()
    print("fecha:", hoy)

    d1, d10 = build_items_retraso_uno_y_diez_dias(
        db, hoy, formato="item_tab", con_enriquecimiento_revision_manual=False
    )
    prej = build_prejudicial_items(db, fecha_referencia=hoy)
    d3 = build_cuotas_pendiente_2_dias_antes_items(db, fecha_referencia=hoy)

    listas = {
        "dia_siguiente": d1,
        "1_cuota": d10,
        "2_cuotas": prej,
        "3_dias_antes": d3,
    }

    # Estados de prestamo de todos los items
    all_pids = sorted({
        int(it["prestamo_id"])
        for items in listas.values()
        for it in items
        if it.get("prestamo_id") is not None
    })
    estados = {}
    if all_pids:
        # chunk
        for i in range(0, len(all_pids), 2000):
            batch = all_pids[i:i+2000]
            for pid, est in db.execute(
                select(Prestamo.id, Prestamo.estado).where(Prestamo.id.in_(batch))
            ).all():
                estados[int(pid)] = (est or "").strip().upper()

    for nombre, items in listas.items():
        mal_prestamo = []
        mal_cliente = []
        for it in items:
            pid = it.get("prestamo_id")
            try:
                pid_i = int(pid) if pid is not None else None
            except (TypeError, ValueError):
                pid_i = None
            est = estados.get(pid_i, "") if pid_i else ""
            if est in ("LIQUIDADO", "DESISTIMIENTO", "FINIQUITO"):
                mal_prestamo.append((pid_i, est, it.get("cedula"), it.get("cliente_id")))
            # corte de envio
            bloq, motivo = item_bloqueado_para_envio_notificacion(db, it)
            if bloq:
                mal_cliente.append((pid_i, motivo, it.get("cedula"), it.get("cliente_id")))
        print(f"{nombre}: {len(items)} items | prestamo LIQ/DES/FIN: {len(mal_prestamo)} | bloqueados al envio: {len(mal_cliente)}")
        for row in mal_prestamo[:5]:
            print("   PRESTAMO:", row)
        for row in mal_cliente[:5]:
            print("   ENVIO:", row)

    # Totales cartera
    estado_norm = func.upper(func.trim(func.coalesce(Prestamo.estado, "")))
    n_des = db.scalar(select(func.count()).select_from(Prestamo).where(estado_norm == "DESISTIMIENTO"))
    n_liq = db.scalar(select(func.count()).select_from(Prestamo).where(estado_norm == "LIQUIDADO"))
    n_fin = db.scalar(select(func.count()).select_from(Prestamo).where(estado_norm == "FINIQUITO"))
    print(f"cartera: DESISTIMIENTO={n_des} LIQUIDADO={n_liq} FINIQUITO={n_fin}")

    # Clientes con DESISTIMIENTO que aparecen en alguna lista (por cliente_id)
    cids_listas = {
        int(it["cliente_id"])
        for items in listas.values()
        for it in items
        if it.get("cliente_id") is not None
    }
    con_des = 0
    solo_liq = 0
    for cid in list(cids_listas)[:]:  # all
        if cliente_tiene_prestamo_desistimiento(db, cid):
            con_des += 1
        elif cliente_sin_cartera_activa_notif(db, cid):
            solo_liq += 1
    print(f"clientes en listas con algun DESISTIMIENTO: {con_des}")
    print(f"clientes en listas sin cartera activa (solo LIQ/DES): {solo_liq}")
finally:
    db.close()
print("AUDITORIA OK")