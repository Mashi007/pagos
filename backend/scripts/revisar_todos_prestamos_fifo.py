#!/usr/bin/env python3
"""
Revisa todos los préstamos en la BD y lista los que tienen violación FIFO
(cuota posterior pagada y anterior no). Opcionalmente rearticula todos.

Uso:
  cd backend
  python scripts/revisar_todos_prestamos_fifo.py              # solo listar
  python scripts/revisar_todos_prestamos_fifo.py --rearticular  # listar y rearticular todos
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

env_path = os.path.join(os.path.dirname(BACKEND), ".env")
if os.path.isfile(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))

SQL_PRESTAMOS_VIOLACION = """
SELECT DISTINCT a.prestamo_id
FROM cuotas a
JOIN cuotas b
  ON b.prestamo_id = a.prestamo_id AND b.numero_cuota = a.numero_cuota + 1
WHERE COALESCE(a.total_pagado, 0) < (a.monto_cuota - 0.01)
  AND COALESCE(b.total_pagado, 0) >= (b.monto_cuota - 0.01)
ORDER BY a.prestamo_id
"""


def main():
    from sqlalchemy import text
    from app.core.database import SessionLocal

    rearticular = "--rearticular" in sys.argv

    db = SessionLocal()
    try:
        rows = db.execute(text(SQL_PRESTAMOS_VIOLACION)).fetchall()
        prestamo_ids = [r[0] for r in rows]
    finally:
        db.close()

    if not prestamo_ids:
        print("No hay préstamos con violación FIFO.")
        return 0

    print(f"Préstamos con violación FIFO: {len(prestamo_ids)}")
    print("prestamo_id:", ", ".join(str(p) for p in prestamo_ids))

    if not rearticular:
        print("\nPara rearticular todos, ejecuta: python scripts/revisar_todos_prestamos_fifo.py --rearticular")
        return 0

    from scripts.rearticular_prestamo_fifo import rearticular_prestamo

    ok = 0
    fail = 0
    for pid in prestamo_ids:
        r = rearticular_prestamo(pid)
        if r.get("ok"):
            ok += 1
            print(f"  {pid}: OK - {r.get('message', '')}")
        else:
            fail += 1
            print(f"  {pid}: ERROR - {r.get('message', '')}")

    print(f"\nRearticulados: {ok}, errores: {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
