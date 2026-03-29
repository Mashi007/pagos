"""
Reaplica cascada para prestamos donde algun pago tiene
sum(cuota_pagos) > monto_pagado + 0.02 (mismo criterio que consultas SQL de auditoria).

Uso (desde carpeta backend):
  python scripts/reaplicar_prestamos_desajuste_monto.py --dry-run
  python scripts/reaplicar_prestamos_desajuste_monto.py --limit 10
  python scripts/reaplicar_prestamos_desajuste_monto.py

Opcional: --skip N  (omitir los N primeros en el orden de prioridad).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo


def _mensaje_duplicado_huella_pago(exc: Exception) -> str | None:
    """Si el fallo es por ux_pagos_fingerprint_activos, devuelve texto de ayuda."""
    s = f"{type(exc).__name__}: {exc!s}"
    if "ux_pagos_fingerprint_activos" not in s and "UniqueViolation" not in s:
        return None
    return (
        "Huella duplicada (prestamo + fecha_pago + monto + ref_norm): hay dos pagos "
        "activos que normalizan a la misma referencia. Corrija datos: distinto "
        "numero_documento o referencia_pago en uno de los pagos (el modelo recalcula "
        "ref_norm al guardar). Consulta ejemplo:\n"
        "  SELECT id, prestamo_id, cedula, fecha_pago::date, monto_pagado, "
        "numero_documento, referencia_pago, ref_norm, estado, conciliado\n"
        "  FROM pagos WHERE prestamo_id = 1822  /* sustituya 1822 por su prestamo_id */\n"
        "  ORDER BY id;"
    )

SQL_IDS = """
WITH desajuste AS (
  SELECT
    x.prestamo_id,
    COUNT(*) AS pagos_con_sobresuma
  FROM (
    SELECT
      p.id,
      p.prestamo_id,
      p.monto_pagado,
      COALESCE((
        SELECT SUM(cp.monto_aplicado)
        FROM cuota_pagos cp
        WHERE cp.pago_id = p.id
      ), 0) AS suma_aplicada
    FROM pagos p
  ) x
  WHERE x.suma_aplicada > x.monto_pagado + 0.02
    AND x.prestamo_id IS NOT NULL
  GROUP BY x.prestamo_id
),
numerado AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY pagos_con_sobresuma DESC, prestamo_id) AS orden,
    prestamo_id
  FROM desajuste
)
SELECT prestamo_id FROM numerado ORDER BY orden
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="Max prestamos a procesar")
    ap.add_argument("--skip", type=int, default=0, help="Saltar los primeros N del orden")
    args = ap.parse_args()

    db_list: Session = SessionLocal()
    try:
        rows = db_list.execute(text(SQL_IDS)).scalars().all()
        ids = [int(r) for r in rows]
        if args.skip:
            ids = ids[args.skip :]
        if args.limit is not None:
            ids = ids[: args.limit]
        print(f"prestamos_a_procesar={len(ids)} (total_en_bd={len(rows)} skip={args.skip})")
        if args.dry_run:
            print("primeros_20:", ids[:20])
            return
    finally:
        db_list.close()

    # Una sesion por prestamo: si PostgreSQL corta SSL u operacion falla a medias,
    # la siguiente iteracion no hereda transaccion invalida (PendingRollbackError).
    ok_n = 0
    fail_n = 0
    for i, pid in enumerate(ids, start=1):
        db: Session = SessionLocal()
        try:
            r = reset_y_reaplicar_cascada_prestamo(db, pid)
            if r.get("ok"):
                db.commit()
                ok_n += 1
                print(f"[{i}/{len(ids)}] OK prestamo_id={pid} {r}")
            else:
                db.rollback()
                fail_n += 1
                print(f"[{i}/{len(ids)}] FAIL prestamo_id={pid} {r}")
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            fail_n += 1
            print(f"[{i}/{len(ids)}] ERROR prestamo_id={pid} {e!r}")
            hint = _mensaje_duplicado_huella_pago(e)
            if hint:
                print(hint)
        finally:
            db.close()

    print(f"resumen: ok={ok_n} fail={fail_n}")


if __name__ == "__main__":
    main()
