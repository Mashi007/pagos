#!/usr/bin/env python3
"""Diagnóstico escáner / cobros por cédula (V/E/J + número)."""
from __future__ import annotations

import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
_REPO = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import text
from app.core.database import SessionLocal

CEDULA_NUM = (sys.argv[1] if len(sys.argv) > 1 else "27974365").strip().replace("-", "").upper()
# Probar V y E
VARIANTES = []
if CEDULA_NUM and CEDULA_NUM[0] in "VEJ":
    VARIANTES.append(CEDULA_NUM)
else:
    VARIANTES.extend([f"V{CEDULA_NUM}", f"E{CEDULA_NUM}"])


def main() -> int:
    db = SessionLocal()
    try:
        print(f"=== Cédula consultada: {CEDULA_NUM} (variantes: {VARIANTES}) ===\n")

        for ced in VARIANTES:
            cli = db.execute(
                text(
                    """
                    SELECT id, cedula, nombres
                    FROM clientes
                    WHERE UPPER(REPLACE(TRIM(cedula), '-', '')) = :ced
                    LIMIT 3
                    """
                ),
                {"ced": ced},
            ).fetchall()
            if cli:
                print(f"CLIENTE ({ced}):")
                for row in cli:
                    print(f"  id={row[0]} cedula={row[1]} nombre={row[2]}")
                print()

        ced_like = f"%{CEDULA_NUM}%"
        borr = db.execute(
            text(
                """
                SELECT b.id, b.estado, b.cedula_normalizada, b.comprobante_nombre,
                       b.created_at, b.pago_reportado_id, b.usuario_id,
                       LENGTH(i.imagen_data) AS bytes_img
                FROM infopagos_escaner_borrador b
                LEFT JOIN pago_comprobante_imagen i ON i.id = b.comprobante_imagen_id
                WHERE b.cedula_normalizada ILIKE :pat
                   OR REPLACE(UPPER(b.cedula_normalizada), '-', '') IN :vars
                ORDER BY b.created_at DESC
                LIMIT 15
                """
            ),
            {"pat": ced_like, "vars": tuple(VARIANTES)},
        ).fetchall()

        print("BORRADORES ESCANER (últimos 15):")
        if not borr:
            print("  (ninguno)")
        else:
            for row in borr:
                limbo = row[1] == "borrador" and row[5] is None
                tag = "LIMBO" if limbo else row[1]
                print(
                    f"  [{tag}] id={row[0]} cedula={row[2]} archivo={row[3]} "
                    f"creado={row[4]} pago_reportado_id={row[5]} usuario={row[6]} bytes={row[7]}"
                )
        print()

        pr = db.execute(
            text(
                """
                SELECT id, referencia_interna, estado, created_at,
                       numero_operacion, monto, moneda, comprobante_imagen_id
                FROM pagos_reportados
                WHERE REPLACE(UPPER(COALESCE(cedula_normalizada, '')), '-', '') IN :vars
                   OR REPLACE(UPPER(COALESCE(tipo_cedula, '') || COALESCE(numero_cedula, '')), '-', '') IN :vars
                ORDER BY created_at DESC
                LIMIT 10
                """
            ),
            {"vars": tuple(VARIANTES)},
        ).fetchall()

        print("PAGOS REPORTADOS (últimos 10):")
        if not pr:
            print("  (ninguno)")
        else:
            for row in pr:
                print(
                    f"  id={row[0]} ref={row[1]} estado={row[2]} creado={row[3]} "
                    f"op={row[4]} monto={row[5]} {row[6]} img={row[7]}"
                )
        print()

        n_limbo = sum(1 for r in borr if r[1] == "borrador" and r[5] is None)
        n_conf = sum(1 for r in borr if r[1] == "confirmado")
        print(
            f"RESUMEN borradores listados: limbo={n_limbo} confirmados={n_conf} "
            f"reportes={len(pr)}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
