#!/usr/bin/env python3
"""
Diagnostico control 7 (total pagos operativos vs suma cuota_pagos), prioridad CRITICA primero.

Cola fija (diff mas grande, hipotesis Bs como USD): prestamos 255, 1513, 201, 2164, 164.
Solo lectura: imprime resumen por prestamo y filas de pagos operativos con perfil moneda.

Tras revisar comprobantes, corregir con:
  python scripts/corregir_pago_bs_y_usd_desde_tasa.py --pago-id ID --monto-bs X [--apply]
Luego por prestamo:
  python scripts/rearticular_prestamo_fifo.py PRESTAMO_ID
o API admin reaplicar-cascada-aplicacion.

Uso (desde carpeta backend, con .env / DATABASE_URL):
  python scripts/diagnostico_control_7_prioridad_critica.py
  python scripts/diagnostico_control_7_prioridad_critica.py --csv
  python scripts/diagnostico_control_7_prioridad_critica.py --prestamo-id 255
  python scripts/diagnostico_control_7_prioridad_critica.py --siguiente-nivel
        # anade 3613,1322,321,1514,274,442,1324,280,9 despues de los 5 criticos
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

env_path = os.path.join(os.path.dirname(BACKEND), ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402

# Control 7: prioridad critica (diff ~24k–95k USD en captura operativa).
PRESTAMOS_PRIORIDAD_CRITICA: tuple[int, ...] = (255, 1513, 201, 2164, 164)

# Segundo bloque (alta/media/baja) si se pide --siguiente-nivel
PRESTAMOS_SIGUIENTE_NIVEL: tuple[int, ...] = (
    3613,
    1322,
    321,
    1514,
    274,
    442,
    1324,
    280,
    9,
)

# True si el pago debe excluirse de totales (mismo criterio que auditoria cartera).
_PAGO_EXCLUIDO = """
(
  UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
  OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
  OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
  OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
)
"""

SQL_RESUMEN = """
SELECT
  pr.id AS prestamo_id,
  pr.estado,
  TRIM(BOTH FROM pr.cedula) AS cedula,
  COALESCE(sp.s, 0)::numeric(18, 2) AS suma_pagos_operativos_usd,
  COALESCE(sa.s, 0)::numeric(18, 2) AS suma_aplicado_cuota_pagos_usd,
  ABS(COALESCE(sp.s, 0) - COALESCE(sa.s, 0))::numeric(18, 4) AS diff_usd
FROM prestamos pr
LEFT JOIN LATERAL (
  SELECT SUM(pg.monto_pagado) AS s FROM pagos pg
  WHERE pg.prestamo_id = pr.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sp ON TRUE
LEFT JOIN LATERAL (
  SELECT SUM(cp.monto_aplicado) AS s
  FROM cuotas cu
  JOIN cuota_pagos cp ON cp.cuota_id = cu.id
  JOIN pagos pg ON pg.id = cp.pago_id
  WHERE cu.prestamo_id = pr.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sa ON TRUE
WHERE pr.id = ANY(:ids)
ORDER BY diff_usd DESC NULLS LAST, pr.id
"""


def _sql_detalle_pagos(ordered_prestamo_ids: list[int]) -> str:
    when_parts = "\n".join(f"    WHEN {pid} THEN {i}" for i, pid in enumerate(ordered_prestamo_ids))
    return f"""
SELECT
  p.prestamo_id,
  p.id AS pago_id,
  CAST(p.fecha_pago AS date) AS fecha_pago,
  p.estado AS estado_pago,
  p.conciliado,
  UPPER(TRIM(COALESCE(p.moneda_registro, ''))) AS moneda_registro,
  p.monto_pagado::numeric AS monto_pagado_usd,
  p.monto_bs_original::numeric AS monto_bs_original,
  p.tasa_cambio_bs_usd::numeric AS tasa_en_pago,
  t.tasa_oficial::numeric AS tasa_tabla_fecha_pago,
  COALESCE((
    SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p.id
  ), 0)::numeric AS suma_aplicado_cuotas,
  CASE
    WHEN COALESCE(p.tasa_cambio_bs_usd, t.tasa_oficial) IS NOT NULL
      AND COALESCE(p.tasa_cambio_bs_usd, t.tasa_oficial) > 0
    THEN ROUND(
      (p.monto_pagado::numeric / NULLIF(COALESCE(p.tasa_cambio_bs_usd, t.tasa_oficial), 0)), 2
    )
    ELSE NULL
  END AS si_monto_pagado_fuese_bs_cuanto_usd,
  CASE
    WHEN UPPER(TRIM(COALESCE(p.moneda_registro, ''))) = 'BS'
      AND p.monto_bs_original IS NOT NULL
      AND COALESCE(p.tasa_cambio_bs_usd, 0) > 0
      AND ROUND((p.monto_bs_original::numeric / p.tasa_cambio_bs_usd::numeric), 2)
        = ROUND(p.monto_pagado::numeric, 2)
    THEN 'BS_coherente'
    WHEN UPPER(TRIM(COALESCE(p.moneda_registro, ''))) = 'BS'
    THEN 'BS_revisar_conversion'
    WHEN COALESCE(p.monto_bs_original, 0) = 0
      AND UPPER(TRIM(COALESCE(p.moneda_registro, ''))) <> 'BS'
      AND p.monto_pagado > 2500
    THEN 'sospecha_bs_como_usd_sin_traza'
    ELSE 'otro'
  END AS perfil
FROM pagos p
LEFT JOIN tasas_cambio_diaria t ON t.fecha = CAST(p.fecha_pago AS date)
WHERE p.prestamo_id = ANY(:ids)
  AND NOT {_PAGO_EXCLUIDO}
ORDER BY
  CASE p.prestamo_id
{when_parts}
    ELSE 999
  END,
  p.fecha_pago,
  p.id
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnostico control 7: prioridad critica primero.")
    ap.add_argument(
        "--siguiente-nivel",
        action="store_true",
        help="Incluye ademas los otros 9 prestamos de la cola de 14 (despues de los 5 criticos).",
    )
    ap.add_argument("--prestamo-id", type=int, default=None, help="Solo este prestamo (ignora cola fija).")
    ap.add_argument("--csv", action="store_true", help="Salida detalle en CSV a stdout.")
    args = ap.parse_args()

    if args.prestamo_id is not None:
        ids_tuple = (args.prestamo_id,)
        orden = [args.prestamo_id]
    elif args.siguiente_nivel:
        ids_tuple = tuple(dict.fromkeys(PRESTAMOS_PRIORIDAD_CRITICA + PRESTAMOS_SIGUIENTE_NIVEL))
        orden = list(ids_tuple)
    else:
        ids_tuple = PRESTAMOS_PRIORIDAD_CRITICA
        orden = list(ids_tuple)

    db = SessionLocal()
    try:
        resumen = db.execute(text(SQL_RESUMEN), {"ids": list(ids_tuple)}).mappings().all()
        by_id = {int(r["prestamo_id"]): r for r in resumen}

        print("=== Control 7 — resumen (orden: prioridad critica primero) ===")
        for pid in orden:
            r = by_id.get(pid)
            if not r:
                print(f"prestamo_id={pid} no encontrado en prestamos o sin fila resumen")
                continue
            print(
                f"id={r['prestamo_id']} estado={r['estado']} cedula={r['cedula']} "
                f"suma_pagos={r['suma_pagos_operativos_usd']} aplicado={r['suma_aplicado_cuota_pagos_usd']} "
                f"diff={r['diff_usd']}"
            )

        detalle_sql = _sql_detalle_pagos(orden)

        rows = db.execute(text(detalle_sql), {"ids": list(ids_tuple)}).mappings().all()

        if args.csv:
            w = csv.DictWriter(
                sys.stdout,
                fieldnames=list(rows[0].keys()) if rows else [],
                extrasaction="ignore",
            )
            if rows:
                w.writeheader()
                for row in rows:
                    w.writerow(dict(row))
            return 0

        print("\n=== Pagos operativos (detalle) ===")
        cur_pid: int | None = None
        for row in rows:
            pid = int(row["prestamo_id"])
            if pid != cur_pid:
                cur_pid = pid
                print(f"\n--- prestamo_id={pid} ---")
            print(
                f"  pago_id={row['pago_id']} fecha={row['fecha_pago']} conciliado={row['conciliado']} "
                f"moneda={row['moneda_registro']!r} monto_usd={row['monto_pagado_usd']} "
                f"bs_orig={row['monto_bs_original']} tasa_pago={row['tasa_en_pago']} "
                f"tasa_tabla={row['tasa_tabla_fecha_pago']} aplicado={row['suma_aplicado_cuotas']} "
                f"si_fuese_bs->usd={row['si_monto_pagado_fuese_bs_cuanto_usd']} perfil={row['perfil']}"
            )

        sospecha = [r for r in rows if r["perfil"] == "sospecha_bs_como_usd_sin_traza"]
        if sospecha:
            print("\n=== Atencion: filas perfil sospecha_bs_como_usd_sin_traza ===")
            for r in sospecha:
                print(f"  prestamo_id={r['prestamo_id']} pago_id={r['pago_id']} monto_pagado={r['monto_pagado_usd']}")

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
