#!/usr/bin/env python3
"""
Script para vincular pagos a cuotas (backfill pago_id).
Para cuotas que ya tienen fecha_pago pero no pago_id, asigna el pago_id del pago
que coincide por prestamo_id y fecha_pago.

Uso: python -m app.scripts.backfill_pago_id_en_cuotas
O desde backend/: python scripts/backfill_pago_id_en_cuotas.py
"""
import os
import sys

# Asegurar que el backend está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.cuota import Cuota
from app.models.pago import Pago


def backfill_pago_id(db: Session, dry_run: bool = True, limite: int = 5000) -> dict:
    """
    Vincula cuotas (fecha_pago no nula, pago_id nulo) con pagos por prestamo_id y fecha.
    Si hay un solo pago por prestamo+fecha, asigna. Si hay varios, distribuye por monto.
    """
    cuotas_sin_pago = db.execute(
        select(Cuota)
        .where(Cuota.fecha_pago.isnot(None), Cuota.pago_id.is_(None))
        .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
    ).scalars().all()
    cuotas_sin_pago = [c[0] for c in cuotas_sin_pago][:limite]

    pagos_sin_vincular = db.execute(
        select(Pago)
        .where(Pago.prestamo_id.isnot(None))
        .where(~select(1).where(Cuota.pago_id == Pago.id).exists())
        .order_by(Pago.id)
    ).scalars().all()
    # Simplificar: pagos que no tienen ninguna cuota con pago_id = su id
    pagos_sin_vincular = []
    todos_pagos = db.execute(select(Pago).where(Pago.prestamo_id.isnot(None)).order_by(Pago.id)).scalars().all()
    for row in todos_pagos:
        p = row[0]
        tiene = db.execute(select(Cuota.id).where(Cuota.pago_id == p.id).limit(1)).first()
        if not tiene:
            pagos_sin_vincular.append(p)
            if len(pagos_sin_vincular) >= limite:
                break

    actualizados = 0
    for cuota in cuotas_sin_pago:
        fecha_c = cuota.fecha_pago
        if isinstance(fecha_c, date):
            fecha_d = fecha_c
        else:
            fecha_d = fecha_c.date() if hasattr(fecha_c, "date") else None
        if not fecha_d:
            continue
        prestamo_id = cuota.prestamo_id
        monto_c = float(cuota.monto or 0)

        # Buscar pago del mismo préstamo y fecha
        pagos_candidatos = db.execute(
            select(Pago)
            .where(
                Pago.prestamo_id == prestamo_id,
                func.date(Pago.fecha_pago) == fecha_d,
            )
            .order_by(Pago.id)
        ).scalars().all()
        pagos_candidatos = [r[0] for r in pagos_candidatos]

        if len(pagos_candidatos) == 1:
            pago = pagos_candidatos[0]
            # Verificar que el pago no exceda su monto ya asignado
            ya_asignado = db.scalar(
                select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.pago_id == pago.id)
            ) or 0
            if float(ya_asignado or 0) + monto_c <= float(pago.monto_pagado or 0) + 0.01:
                if not dry_run:
                    cuota.pago_id = pago.id
                    actualizados += 1
                else:
                    actualizados += 1
        elif len(pagos_candidatos) > 1:
            # Varios pagos mismo día: asignar al primero que tenga espacio
            for pago in pagos_candidatos:
                ya_asignado = db.scalar(
                    select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(Cuota.pago_id == pago.id)
                ) or 0
                if float(ya_asignado or 0) + monto_c <= float(pago.monto_pagado or 0) + 0.01:
                    if not dry_run:
                        cuota.pago_id = pago.id
                        actualizados += 1
                    else:
                        actualizados += 1
                    break

    if not dry_run and actualizados > 0:
        db.commit()
    return {
        "cuotas_sin_pago_id": len(cuotas_sin_pago),
        "pagos_sin_cuotas_vinculadas": len(pagos_sin_vincular),
        "vinculados": actualizados,
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    limite = 10000
    for a in sys.argv:
        if a.startswith("--limit="):
            limite = int(a.split("=")[1])
    db = SessionLocal()
    try:
        r = backfill_pago_id(db, dry_run=dry, limite=limite)
        print(f"Cuotas sin pago_id encontradas: {r['cuotas_sin_pago_id']}")
        print(f"Pagos sin cuotas vinculadas: {r['pagos_sin_cuotas_vinculadas']}")
        print(f"Vinculados: {r['vinculados']} {'(simulado)' if r['dry_run'] else '(aplicado)'}")
        if dry and r["vinculados"] > 0:
            print("Ejecuta con --apply para aplicar cambios. Ej: python -m app.scripts.backfill_pago_id_en_cuotas --apply")
    finally:
        db.close()
