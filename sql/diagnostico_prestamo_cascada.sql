-- Diagnostico: huérfanos + diff por cuota + diff global + si amerita reaplicacion en CASCADA
-- PostgreSQL. Cambie solo el id en la CTE `prm` (una linea).
--
-- Equivalente API (admin, no modifica datos):
--   GET /api/v1/prestamos/{prestamo_id}/integridad-cuotas
-- Si amerita: POST /api/v1/prestamos/{prestamo_id}/reaplicar-cascada-aplicacion
--   (ruta .../reaplicar-fifo-aplicacion es alias legacy; politica: solo cascada)

WITH prm AS (
  SELECT 2438::int AS prestamo_id
),

pagos_conc AS (
  SELECT pg.*
  FROM pagos pg
  CROSS JOIN prm
  WHERE pg.prestamo_id = prm.prestamo_id
    AND COALESCE(pg.monto_pagado, 0) > 0
    AND (
      pg.conciliado = TRUE
      OR upper(trim(coalesce(pg.verificado_concordancia, ''))) = 'SI'
    )
),

sum_pagos AS (
  SELECT COALESCE(SUM(monto_pagado), 0)::numeric(14, 2) AS suma
  FROM pagos_conc
),

sum_cp AS (
  SELECT COALESCE(SUM(cp.monto_aplicado), 0)::numeric(14, 2) AS suma
  FROM cuota_pagos cp
  JOIN cuotas c ON c.id = cp.cuota_id
  CROSS JOIN prm
  WHERE c.prestamo_id = prm.prestamo_id
),

sum_total_cuotas AS (
  SELECT COALESCE(SUM(c.total_pagado), 0)::numeric(14, 2) AS suma
  FROM cuotas c
  CROSS JOIN prm
  WHERE c.prestamo_id = prm.prestamo_id
),

orphans AS (
  SELECT pc.id AS pago_id, pc.fecha_pago, pc.monto_pagado, pc.numero_documento
  FROM pagos_conc pc
  WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pc.id)
),

cuotas_diff AS (
  SELECT
    c.id AS cuota_id,
    c.numero_cuota,
    c.monto_cuota,
    COALESCE(c.total_pagado, 0)::numeric(14, 2) AS total_pagado,
    COALESCE(SUM(cp.monto_aplicado), 0)::numeric(14, 2) AS sum_cuota_pagos,
    ROUND(
      COALESCE(c.total_pagado, 0)::numeric - COALESCE(SUM(cp.monto_aplicado), 0)::numeric,
      2
    ) AS diff_total_vs_cp
  FROM cuotas c
  CROSS JOIN prm
  LEFT JOIN cuota_pagos cp ON cp.cuota_id = c.id
  WHERE c.prestamo_id = prm.prestamo_id
  GROUP BY c.id, c.numero_cuota, c.monto_cuota, c.total_pagado
  HAVING ABS(COALESCE(c.total_pagado, 0) - COALESCE(SUM(cp.monto_aplicado), 0)) > 0.02
),

dup_pago_misma_cuota AS (
  SELECT cp.cuota_id, cp.pago_id, COUNT(*) AS veces
  FROM cuota_pagos cp
  JOIN cuotas c ON c.id = cp.cuota_id
  CROSS JOIN prm
  WHERE c.prestamo_id = prm.prestamo_id
  GROUP BY cp.cuota_id, cp.pago_id
  HAVING COUNT(*) > 1
),

agg AS (
  SELECT
    (SELECT COUNT(*) FROM orphans) AS n_orphans,
    (SELECT COUNT(*) FROM cuotas_diff) AS n_cuotas_inconsistentes,
    (SELECT COUNT(*) FROM dup_pago_misma_cuota) AS n_duplicados_cuota_pago,
    (SELECT suma FROM sum_pagos) AS sum_monto_pagos_conciliados,
    (SELECT suma FROM sum_cp) AS sum_monto_cuota_pagos,
    (SELECT suma FROM sum_total_cuotas) AS sum_total_pagado_cuotas,
    ROUND(
      (SELECT suma FROM sum_total_cuotas) - (SELECT suma FROM sum_cp),
      2
    ) AS diff_global_total_vs_cp
)

SELECT
  prm.prestamo_id,
  a.n_orphans,
  a.n_cuotas_inconsistentes,
  a.n_duplicados_cuota_pago,
  a.sum_monto_pagos_conciliados,
  a.sum_monto_cuota_pagos,
  a.sum_total_pagado_cuotas,
  a.diff_global_total_vs_cp,
  ROUND(a.sum_monto_pagos_conciliados - a.sum_monto_cuota_pagos, 2) AS diff_pagos_vs_cuota_pagos,
  (
    a.n_orphans > 0
    OR a.n_cuotas_inconsistentes > 0
    OR a.n_duplicados_cuota_pago > 0
    OR ABS(a.diff_global_total_vs_cp) > 0.02
    OR ABS(ROUND(a.sum_monto_pagos_conciliados - a.sum_monto_cuota_pagos, 2)) > 0.02
  ) AS amerita_reaplicacion_cascada,
  CASE
    WHEN (
      a.n_orphans > 0
      OR a.n_cuotas_inconsistentes > 0
      OR a.n_duplicados_cuota_pago > 0
      OR ABS(a.diff_global_total_vs_cp) > 0.02
      OR ABS(ROUND(a.sum_monto_pagos_conciliados - a.sum_monto_cuota_pagos, 2)) > 0.02
    )
    THEN 'SI: ejecutar reaplicacion en cascada (POST reaplicar-cascada-aplicacion) o script SQL de reparacion.'
    ELSE 'OK: no se detectaron desalineaciones con los criterios usados.'
  END AS recomendacion
FROM prm
CROSS JOIN agg a;

-- Detalle opcional: huérfanos (lista). Usar el mismo prestamo_id que arriba.
/*
WITH prm AS (SELECT 2438::int AS prestamo_id)
SELECT
  pg.id AS pago_id,
  pg.fecha_pago,
  pg.monto_pagado,
  pg.numero_documento
FROM pagos pg
CROSS JOIN prm
WHERE pg.prestamo_id = prm.prestamo_id
  AND COALESCE(pg.monto_pagado, 0) > 0
  AND (pg.conciliado = TRUE OR upper(trim(coalesce(pg.verificado_concordancia, ''))) = 'SI')
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pg.id)
ORDER BY pg.fecha_pago NULLS LAST, pg.id;
*/
