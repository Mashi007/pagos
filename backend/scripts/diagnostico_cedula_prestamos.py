#!/usr/bin/env python3
"""
Lista préstamos por cédula: titular (clientes.cedula) vs coincidencia solo en prestamos.cedula.

Uso (desde backend/, DATABASE_URL en .env):
  python scripts/diagnostico_cedula_prestamos.py V13068140
  python scripts/diagnostico_cedula_prestamos.py 13068140
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

_REPO_ROOT = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO_ROOT, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.services.cobros.cobros_publico_reporte_service import prestamos_aprobados_del_cliente
from app.services.prestamo_candidatos_drive_validadores import conteos_cupo_para_una_cedula
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnóstico préstamos por cédula")
    ap.add_argument("cedula", help="Cédula (V13068140, 13068140, etc.)")
    args = ap.parse_args()
    clave = texto_cedula_comparable_bd(args.cedula.strip())
    if not clave:
        print("Cédula inválida o vacía", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        cliente = db.execute(
            select(Cliente).where(
                expr_cedula_normalizada_para_comparar(Cliente.cedula) == clave
            )
        ).scalars().first()
        titular = []
        if cliente:
            rows = db.execute(
                select(Prestamo.id, Prestamo.estado, Prestamo.cedula)
                .where(Prestamo.cliente_id == cliente.id)
                .order_by(Prestamo.id)
            ).all()
            titular = [
                {"id": r[0], "estado": r[1], "prestamo_cedula": r[2]}
                for r in rows
            ]
            aprob_ids = prestamos_aprobados_del_cliente(db, cliente.id)
        else:
            aprob_ids = []

        huérfanos = db.execute(
            select(Prestamo.id, Prestamo.estado, Prestamo.cedula, Prestamo.cliente_id)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                expr_cedula_normalizada_para_comparar(Prestamo.cedula) == clave,
                expr_cedula_normalizada_para_comparar(Cliente.cedula) != clave,
            )
            .order_by(Prestamo.id)
        ).all()
        huerfanos_list = [
            {
                "id": r[0],
                "estado": r[1],
                "prestamo_cedula": r[2],
                "cliente_id": r[3],
            }
            for r in huérfanos
        ]

        cupo = conteos_cupo_para_una_cedula(db, clave)
        out = {
            "cedula_clave": clave,
            "cliente_id": getattr(cliente, "id", None),
            "cliente_cedula": getattr(cliente, "cedula", None) if cliente else None,
            "prestamos_titular": titular,
            "prestamos_aprobados_portal": aprob_ids,
            "prestamos_huérfanos_prestamo_cedula": huerfanos_list,
            "conteos_cupo_titular": cupo,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
