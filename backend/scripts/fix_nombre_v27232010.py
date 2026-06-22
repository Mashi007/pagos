#!/usr/bin/env python3
"""
Correccion puntual: alinear nombre en prestamos con clientes para V27232010.

Contexto: estado de cuenta lee clientes.nombres; recibos (cuota/cartera) leen
prestamos.nombres (snapshot). Si difieren, el PDF de estado de cuenta puede mostrar
un nombre y los recibos otro.

Uso (desde backend/):
  python scripts/fix_nombre_v27232010.py
  python scripts/fix_nombre_v27232010.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
)

CEDULA_INPUT = "V27232010"
NOMBRE_CANONICO = "Yosmary Del Carmen Cardenas Hernandez"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo mostrar cambios sin persistir.",
    )
    args = parser.parse_args()
    cedula_lookup = normalizar_cedula_almacenamiento(CEDULA_INPUT)
    if not cedula_lookup:
        print("Cedula invalida:", CEDULA_INPUT)
        return 1

    db = SessionLocal()
    try:
        cliente = db.execute(
            select(Cliente).where(
                expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup
            )
        ).scalars().first()
        if not cliente:
            print("Cliente no encontrado para", CEDULA_INPUT)
            return 1

        cambios = 0
        nom_cli = (cliente.nombres or "").strip()
        if nom_cli != NOMBRE_CANONICO:
            print(f"clientes.id={cliente.id}: {nom_cli!r} -> {NOMBRE_CANONICO!r}")
            if not args.dry_run:
                cliente.nombres = NOMBRE_CANONICO
            cambios += 1

        prestamos = db.execute(
            select(Prestamo).where(Prestamo.cliente_id == cliente.id)
        ).scalars().all()
        for prestamo in prestamos:
            nom_pre = (prestamo.nombres or "").strip()
            if nom_pre != NOMBRE_CANONICO:
                print(
                    f"prestamos.id={prestamo.id}: {nom_pre!r} -> {NOMBRE_CANONICO!r}"
                )
                if not args.dry_run:
                    prestamo.nombres = NOMBRE_CANONICO
                cambios += 1

        if cambios == 0:
            print("OK: clientes y prestamos ya tienen", NOMBRE_CANONICO)
            return 0

        if args.dry_run:
            print(f"(dry-run) {cambios} cambio(s) pendiente(s)")
            return 0

        db.commit()
        print(f"Listo: {cambios} registro(s) actualizado(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
