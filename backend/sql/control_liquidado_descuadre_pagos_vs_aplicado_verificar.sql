-- =============================================================================
-- Auditoria cartera — control codigo: liquidado_descuadre_total_pagos_vs_aplicado_cuotas
-- (UI: "LIQUIDADO con descuadre: total pagos operativos vs aplicado a cuotas")
--
-- Motor: app/services/prestamo_cartera_auditoria.py (tot_map, diff_ap, _TOL = 0.02)
-- Regla: prestamo.estado = LIQUIDADO y |suma pagos operativos - suma aplicado cuota_pagos| > 0.02
--   - Pagos operativos: mismas exclusiones que cartera (anulados, reversados, duplicado, etc.)
--   - Aplicado: SUM(cuota_pagos.monto_aplicado) solo filas cuyo pago es operativo (join pagos pg)
--
-- Nota: La API puede listar solo un subconjunto de prestamos (filtros/paginacion). Este SQL
-- recorre todos los LIQUIDADO en BD; el conteo puede coincidir con "N casos" si la vista usa
-- la misma poblacion.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Detalle: prestamos LIQUIDADO con descuadre
-- -----------------------------------------------------------------------------
SELECT
  p.id AS prestamo_id,
  p.estado,
  p.cedula,
  sp.sum_pagos::numeric(18, 2) AS sum_monto_pagado_operativo,
  sa.sum_aplicado::numeric(18, 2) AS sum_monto_aplicado_cuotas,
  ABS(sp.sum_pagos - sa.sum_aplicado)::numeric(18, 2) AS diff_abs_usd,
  (sp.sum_pagos - sa.sum_aplicado)::numeric(18, 2) AS neto_operativo_menos_aplicado
FROM prestamos p
LEFT JOIN LATERAL (
  SELECT COALESCE(SUM(pg.monto_pagado), 0)::numeric AS sum_pagos
  FROM pagos pg
  WHERE pg.prestamo_id = p.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sp ON true
LEFT JOIN LATERAL (
  SELECT COALESCE(SUM(cp.monto_aplicado), 0)::numeric AS sum_aplicado
  FROM cuotas cu
  JOIN cuota_pagos cp ON cp.cuota_id = cu.id
  JOIN pagos pg ON pg.id = cp.pago_id
  WHERE cu.prestamo_id = p.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sa ON true
WHERE UPPER(TRIM(BOTH FROM COALESCE(p.estado, ''))) = 'LIQUIDADO'
  AND ABS(sp.sum_pagos - sa.sum_aplicado) > 0.02
ORDER BY diff_abs_usd DESC, p.id;


-- -----------------------------------------------------------------------------
-- 2) Conteo (prestamos LIQUIDADO con ese descuadre)
-- -----------------------------------------------------------------------------
SELECT COUNT(*)::int AS casos_liquidado_descuadre_pagos_vs_aplicado
FROM prestamos p
LEFT JOIN LATERAL (
  SELECT COALESCE(SUM(pg.monto_pagado), 0)::numeric AS sum_pagos
  FROM pagos pg
  WHERE pg.prestamo_id = p.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sp ON true
LEFT JOIN LATERAL (
  SELECT COALESCE(SUM(cp.monto_aplicado), 0)::numeric AS sum_aplicado
  FROM cuotas cu
  JOIN cuota_pagos cp ON cp.cuota_id = cu.id
  JOIN pagos pg ON pg.id = cp.pago_id
  WHERE cu.prestamo_id = p.id
    AND NOT (
      UPPER(COALESCE(pg.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(pg.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(pg.estado, '')) IN ('cancelado', 'rechazado')
    )
) sa ON true
WHERE UPPER(TRIM(BOTH FROM COALESCE(p.estado, ''))) = 'LIQUIDADO'
  AND ABS(sp.sum_pagos - sa.sum_aplicado) > 0.02;
