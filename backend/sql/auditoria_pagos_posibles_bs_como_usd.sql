-- =============================================================================
-- Auditoría: pagos donde el monto en Bs. del reporte quedó copiado en monto_pagado
-- (misma causa que los 6 de marzo 2026). Ejecutar en DBeaver; revisar cada fila.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- A) Patrón fuerte: reporte BS aprobado/importado, operación = referencia_pago,
--    y monto_pagado ≈ monto del reporte (Bs.) → debería ser USD = monto/tasa
-- ---------------------------------------------------------------------------
SELECT
  p.id AS pago_id,
  p.fecha_pago::date AS fecha_pago,
  p.prestamo_id,
  p.monto_pagado AS monto_pagado_actual,
  p.moneda_registro,
  p.monto_bs_original,
  p.tasa_cambio_bs_usd,
  p.referencia_pago,
  p.numero_documento,
  pr.referencia_interna,
  pr.monto AS monto_bs_reporte,
  pr.fecha_pago AS fecha_reporte,
  tc.tasa_oficial,
  ROUND((pr.monto::numeric / NULLIF(tc.tasa_oficial, 0)), 2) AS monto_usd_esperado
FROM pagos p
JOIN pagos_reportados pr
  ON TRIM(BOTH FROM pr.numero_operacion) = TRIM(BOTH FROM p.referencia_pago)
JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND ABS(p.monto_pagado::numeric - pr.monto::numeric) < 0.02
ORDER BY p.monto_pagado DESC;


-- ---------------------------------------------------------------------------
-- B) Mismo patrón A pero SIN fila de tasa (hay que cargar tasa antes de UPDATE)
-- ---------------------------------------------------------------------------
SELECT
  p.id AS pago_id,
  p.fecha_pago::date,
  p.monto_pagado,
  p.referencia_pago,
  pr.referencia_interna,
  pr.fecha_pago AS fecha_reporte_falta_tasa,
  pr.monto AS monto_bs_reporte
FROM pagos p
JOIN pagos_reportados pr
  ON TRIM(BOTH FROM pr.numero_operacion) = TRIM(BOTH FROM p.referencia_pago)
LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND ABS(p.monto_pagado::numeric - pr.monto::numeric) < 0.02
  AND tc.fecha IS NULL
ORDER BY p.fecha_pago DESC;


-- ---------------------------------------------------------------------------
-- C) Heurística: conciliado, moneda NULL o USD, monto_pagado muy alto (revisar
--    si no hay reporte enlazado — puede ser otro origen o error)
-- ---------------------------------------------------------------------------
SELECT
  p.id,
  p.fecha_pago::date,
  p.monto_pagado,
  p.moneda_registro,
  p.referencia_pago,
  p.numero_documento,
  p.prestamo_id,
  p.conciliado
FROM pagos p
WHERE p.conciliado IS TRUE
  AND (p.moneda_registro IS NULL OR LOWER(TRIM(p.moneda_registro)) = 'usd')
  AND p.monto_pagado > 2500
ORDER BY p.monto_pagado DESC
LIMIT 200;


-- ---------------------------------------------------------------------------
-- D) BS declarado pero sin conversión coherente en columnas de auditoría
-- ---------------------------------------------------------------------------
SELECT
  p.id,
  p.fecha_pago::date,
  p.monto_pagado,
  p.moneda_registro,
  p.monto_bs_original,
  p.tasa_cambio_bs_usd,
  p.referencia_pago
FROM pagos p
WHERE LOWER(TRIM(COALESCE(p.moneda_registro, ''))) = 'bs'
  AND (
    p.monto_bs_original IS NULL
    OR COALESCE(p.tasa_cambio_bs_usd, 0) <= 0
    OR ABS(
      p.monto_pagado::numeric
      - (p.monto_bs_original::numeric / NULLIF(p.tasa_cambio_bs_usd, 0))
    ) > 0.10
  )
ORDER BY p.fecha_pago DESC
LIMIT 200;
