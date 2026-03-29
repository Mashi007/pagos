"""
Reaplica cascada en prestamos LIQUIDADO donde la suma de pagos operativos
no cuadra con la suma aplicada a cuotas desde esos pagos (via cuota_pagos),
pero el gap absoluto es menor a un umbral (por defecto 100 USD).

Criterio de sumas alineado con `prestamo_cartera_auditoria.py` (tot_sql / control
total_pagado_vs_aplicado_cuotas): mismos filtros de pago operativo.

Uso (desde carpeta backend):
  python scripts/reaplicar_prestamos_liquidado_gap_menor_100.py --dry-run
  python scripts/reaplicar_prestamos_liquidado_gap_menor_100.py --limit 5
  python scripts/reaplicar_prestamos_liquidado_gap_menor_100.py

Opcional:
  --max-diff-usd 100   (solo gaps estrictamente menores; defecto 100)
  --min-diff-usd 0.02  (ignora diferencias de ruido; defecto 0.02)
  --prestamo-id 253    (repite flag para varios; ignora SQL de rango y solo esos IDs)

Bandas ejemplo (misma consulta que auditoria):
  gap < 100 USD (defecto):  python scripts/reaplicar_prestamos_liquidado_gap_menor_100.py
  [100, 350):               --min-diff-usd 100 --max-diff-usd 350
  [350, 5000):              --min-diff-usd 350 --max-diff-usd 5000
  Un solo coloso:           --prestamo-id 253
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera
from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo


def _mensaje_duplicado_huella_pago(exc: Exception) -> str | None:
    s = f"{type(exc).__name__}: {exc!s}"
    if "ux_pagos_fingerprint_activos" not in s and "UniqueViolation" not in s:
        return None
    return (
        "Huella duplicada: ver scripts/reaplicar_prestamos_desajuste_monto.py (mensaje detallado)."
    )


def sql_ids(max_diff: float, min_diff: float) -> str:
    excl_pg = _sql_fragment_pago_excluido_cartera("pg")
    return f"""
WITH por_prestamo AS (
  SELECT
    pr.id AS prestamo_id,
    COALESCE(sp.s, 0)::numeric AS suma_pagos,
    COALESCE(sa.s, 0)::numeric AS suma_aplicado
  FROM prestamos pr
  LEFT JOIN LATERAL (
    SELECT SUM(pg.monto_pagado) AS s
    FROM pagos pg
    WHERE pg.prestamo_id = pr.id AND NOT {excl_pg}
  ) sp ON true
  LEFT JOIN LATERAL (
    SELECT SUM(cp.monto_aplicado) AS s
    FROM cuotas cu
    JOIN cuota_pagos cp ON cp.cuota_id = cu.id
    JOIN pagos pg ON pg.id = cp.pago_id
    WHERE cu.prestamo_id = pr.id AND NOT {excl_pg}
  ) sa ON true
  WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
)
SELECT prestamo_id
FROM por_prestamo
WHERE ABS(suma_pagos - suma_aplicado) > :min_diff
  AND ABS(suma_pagos - suma_aplicado) < :max_diff
ORDER BY ABS(suma_pagos - suma_aplicado) ASC, prestamo_id
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--max-diff-usd", type=float, default=100.0)
    ap.add_argument("--min-diff-usd", type=float, default=0.02)
    ap.add_argument(
        "--prestamo-id",
        type=int,
        action="append",
        dest="prestamo_ids",
        default=None,
        help="Solo estos prestamo_id (repetir flag). Omite el filtro por rango de gap.",
    )
    args = ap.parse_args()

    if args.prestamo_ids:
        ids = sorted({int(x) for x in args.prestamo_ids if x is not None})
        if args.skip:
            ids = ids[args.skip :]
        if args.limit is not None:
            ids = ids[: args.limit]
        print(
            f"prestamos_a_procesar={len(ids)} (modo --prestamo-id explicito, skip={args.skip})"
        )
        if args.dry_run:
            print("ids:", ids)
            return
    else:
        if args.max_diff_usd <= args.min_diff_usd:
            print("max-diff-usd debe ser mayor que min-diff-usd")
            sys.exit(1)

        q = text(sql_ids(args.max_diff_usd, args.min_diff_usd))
        db_list: Session = SessionLocal()
        try:
            rows = db_list.execute(
                q, {"min_diff": args.min_diff_usd, "max_diff": args.max_diff_usd}
            ).fetchall()
            ids = [int(r[0]) for r in rows]
            if args.skip:
                ids = ids[args.skip :]
            if args.limit is not None:
                ids = ids[: args.limit]
            print(
                f"prestamos_a_procesar={len(ids)} "
                f"(total_en_criterio={len(rows)} skip={args.skip} "
                f"gap en ({args.min_diff_usd}, {args.max_diff_usd}) USD LIQUIDADO)"
            )
            if args.dry_run:
                print("ordenados por gap ascendente:", ids)
                return
        finally:
            db_list.close()

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
