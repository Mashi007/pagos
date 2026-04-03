-- =============================================================================
-- Control 5: pagos_mismo_dia_monto (auditoria cartera)
-- Motor: backend/app/services/prestamo_cartera_auditoria.py
--
-- Regla: mismo prestamo_id + misma fecha calendario (fecha_pago) + mismo monto_pagado,
-- al menos 2 pagos operativos (no anulados/reversados/etc.).
-- Excluye filas con pagos.excluir_control_pagos_mismo_dia_monto = true (Visto admin; ver migracion_control5_visto).
--
-- El conteo "casos" en UI = prestamos distintos con SI (no numero de filas duplicadas).
-- Solo SELECT; no modifica datos.
-- =============================================================================

-- Fragmento: pago excluido (alias p)

/*
(
  UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
  OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
  OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
  OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
)
*/


-- -----------------------------------------------------------------------------
-- PASO 1 — Prestamos con control 5 en SI (lista para filtro auditoria)
-- -----------------------------------------------------------------------------
SELECT DISTINCT t.prestamo_id
FROM (
  SELECT
    p.prestamo_id,
    CAST(p.fecha_pago AS date) AS fd,
    p.monto_pagado,
    COUNT(*) AS cnt
  FROM pagos p
  WHERE p.prestamo_id IS NOT NULL
    AND NOT COALESCE(p.excluir_control_pagos_mismo_dia_monto, false)
    AND NOT (
      UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
    )
  GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado
  HAVING COUNT(*) > 1
) t
ORDER BY t.prestamo_id;


-- -----------------------------------------------------------------------------
-- PASO 2 — Grupos duplicados (prestamo + fecha + monto) con cantidad de filas
-- -----------------------------------------------------------------------------
SELECT
  p.prestamo_id,
  CAST(p.fecha_pago AS date) AS fecha_pago,
  p.monto_pagado::numeric(18, 2) AS monto_pagado,
  COUNT(*)::int AS num_pagos_en_grupo
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND NOT COALESCE(p.excluir_control_pagos_mismo_dia_monto, false)
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
    OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado
HAVING COUNT(*) > 1
ORDER BY p.prestamo_id, fecha_pago, p.monto_pagado;


-- -----------------------------------------------------------------------------
-- PASO 3 — Detalle de cada pago involucrado (ids, documento, conciliado)
-- -----------------------------------------------------------------------------
WITH dup AS (
  SELECT prestamo_id, CAST(fecha_pago AS date) AS fd, monto_pagado
  FROM pagos p
  WHERE p.prestamo_id IS NOT NULL
    AND NOT COALESCE(p.excluir_control_pagos_mismo_dia_monto, false)
    AND NOT (
      UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
    )
  GROUP BY prestamo_id, CAST(fecha_pago AS date), monto_pagado
  HAVING COUNT(*) > 1
)
SELECT
  p.id AS pago_id,
  p.prestamo_id,
  CAST(p.fecha_pago AS date) AS fecha_pago,
  p.monto_pagado::numeric(18, 2) AS monto_pagado,
  p.conciliado,
  UPPER(TRIM(COALESCE(p.estado, ''))) AS estado_pago,
  LEFT(TRIM(COALESCE(p.numero_documento, '')), 40) AS numero_documento,
  LEFT(TRIM(COALESCE(p.referencia_pago, '')), 40) AS referencia_pago,
  LEFT(TRIM(COALESCE(p.ref_norm, '')), 40) AS ref_norm
FROM pagos p
JOIN dup d
  ON d.prestamo_id = p.prestamo_id
  AND d.fd = CAST(p.fecha_pago AS date)
  AND d.monto_pagado = p.monto_pagado
WHERE NOT COALESCE(p.excluir_control_pagos_mismo_dia_monto, false)
  AND NOT (
  UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
  OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
  OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
  OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
)
ORDER BY p.prestamo_id, p.fecha_pago, p.monto_pagado, p.id;
