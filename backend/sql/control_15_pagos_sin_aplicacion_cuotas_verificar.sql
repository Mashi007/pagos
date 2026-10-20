-- Control 15: pagos_sin_aplicacion_a_cuotas (limbo accionable)
-- Titulo UI: "Pagos operativos sin aplicacion a cuotas con cupo pendiente (limbo)"
-- Misma regla que `prestamo_cartera_auditoria.py` (AUDITORIA_CARTERA_REGLAS_VERSION >= 24).
--
-- Alerta SI si existe pago operativo con monto_pagado > 0 que:
--   (1) no tiene fila en cuota_pagos, o sum aplicado < monto - 0.02, Y
--   (2) el prestamo aun tiene cupo en cuotas (PENDIENTE/VENCIDO/MORA/PARCIAL con saldo > 0.01)
--
-- Remanente sin cupo: control aparte `pagos_remanente_sin_cupo` (bloque 1b abajo).
-- Excluye pagos no operativos: ver _sql_fragment_pago_excluido_cartera en el backend.

-- === 1) Limbo accionable (hay cupo) ===
SELECT DISTINCT p.prestamo_id
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
    OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
  AND (
    NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
    OR COALESCE((
         SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p.id
       ), 0) < (p.monto_pagado::numeric - 0.02)
  )
  AND EXISTS (
    SELECT 1 FROM cuotas c
    WHERE c.prestamo_id = p.prestamo_id
      AND UPPER(TRIM(COALESCE(c.estado, ''))) IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')
      AND (COALESCE(c.monto, 0) - COALESCE(c.total_pagado, 0)) > 0.01
  )
ORDER BY p.prestamo_id;

-- === 1b) Remanente sin cupo (no forzar cascada) ===
SELECT DISTINCT p.prestamo_id
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
    OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
  AND (
    NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
    OR COALESCE((
         SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p.id
       ), 0) < (p.monto_pagado::numeric - 0.02)
  )
  AND NOT EXISTS (
    SELECT 1 FROM cuotas c
    WHERE c.prestamo_id = p.prestamo_id
      AND UPPER(TRIM(COALESCE(c.estado, ''))) IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')
      AND (COALESCE(c.monto, 0) - COALESCE(c.total_pagado, 0)) > 0.01
  )
ORDER BY p.prestamo_id;

-- === 2) Detalle por pago (equivalente a GET control-15 / listar_pagos_sin_aplicacion_cuotas_por_prestamo) ===
-- Sustituir :pid por el prestamo_id (ej. 3805).
/*
SELECT
  p.id AS pago_id,
  p.prestamo_id,
  p.fecha_pago,
  p.monto_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS sum_monto_aplicado,
  (p.monto_pagado::numeric - COALESCE(SUM(cp.monto_aplicado), 0)) AS saldo_sin_aplicar_usd,
  CASE
    WHEN NOT EXISTS (SELECT 1 FROM cuota_pagos cp0 WHERE cp0.pago_id = p.id)
    THEN 'sin_filas_cuota_pagos'
    ELSE 'sum_aplicado_menor_que_monto_menos_tol'
  END AS motivo
FROM pagos p
LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
WHERE p.prestamo_id = :pid
  AND p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
    OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
GROUP BY p.id, p.prestamo_id, p.fecha_pago, p.monto_pagado
HAVING
  NOT EXISTS (SELECT 1 FROM cuota_pagos cp1 WHERE cp1.pago_id = p.id)
  OR COALESCE(SUM(cp.monto_aplicado), 0) < (p.monto_pagado::numeric - 0.02)
ORDER BY p.fecha_pago NULLS LAST, p.id;
*/

-- === 3) Todos los pagos en condicion (todas las filas, todos los prestamos) ===
SELECT
  p.id AS pago_id,
  p.prestamo_id,
  p.fecha_pago,
  p.monto_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS sum_monto_aplicado,
  (p.monto_pagado::numeric - COALESCE(SUM(cp.monto_aplicado), 0)) AS saldo_sin_aplicar_usd,
  CASE
    WHEN NOT EXISTS (SELECT 1 FROM cuota_pagos cp0 WHERE cp0.pago_id = p.id)
    THEN 'sin_filas_cuota_pagos'
    ELSE 'sum_aplicado_menor_que_monto_menos_tol'
  END AS motivo
FROM pagos p
LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT (
    UPPER(COALESCE(p.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
    OR UPPER(COALESCE(p.estado, '')) LIKE '%ANUL%'
    OR UPPER(COALESCE(p.estado, '')) LIKE '%REVERS%'
    OR LOWER(COALESCE(p.estado, '')) IN ('cancelado', 'rechazado')
  )
GROUP BY p.id, p.prestamo_id, p.fecha_pago, p.monto_pagado
HAVING
  NOT EXISTS (SELECT 1 FROM cuota_pagos cp1 WHERE cp1.pago_id = p.id)
  OR COALESCE(SUM(cp.monto_aplicado), 0) < (p.monto_pagado::numeric - 0.02)
ORDER BY p.prestamo_id, p.fecha_pago NULLS LAST, p.id;

-- === 4) Filas en cuota_pagos + datos de la cuota (un pago o lista de pago_id) ===
-- Sustituir la lista IN por los pago_id que quieras auditar (ej. salida del bloque 3).
-- Si un pago no devuelve filas aqui, es coherente con motivo sin_filas_cuota_pagos.

SELECT
  cp.id AS cuota_pago_id,
  cp.pago_id,
  cp.cuota_id,
  cp.monto_aplicado,
  cp.fecha_aplicacion,
  cp.orden_aplicacion,
  cp.es_pago_completo,
  cu.prestamo_id,
  cu.numero_cuota,
  cu.fecha_vencimiento,
  cu.monto_cuota,
  COALESCE(cu.total_pagado, 0) AS cuota_total_pagado,
  cu.estado AS cuota_estado
FROM cuota_pagos cp
JOIN cuotas cu ON cu.id = cp.cuota_id
WHERE cp.pago_id IN (
  59992, 59997, 59998, 59805, 59901, 59944, 52688, 59945, 59946, 59938,
  51789, 60011, 60007, 51790, 53214, 58473, 59860, 59927, 50790, 59818
)
ORDER BY cp.pago_id, cp.orden_aplicacion, cp.id;

-- === 5) Resumen por pago: monto_pagado vs sum(cuota_pagos) y n filas de aplicacion ===
-- Misma lista IN que arriba (o la que corresponda).

SELECT
  p.id AS pago_id,
  p.prestamo_id,
  p.fecha_pago,
  p.monto_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS sum_monto_aplicado,
  (p.monto_pagado::numeric - COALESCE(SUM(cp.monto_aplicado), 0)) AS saldo_sin_aplicar_usd,
  COUNT(cp.id) AS filas_cuota_pagos
FROM pagos p
LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
WHERE p.id IN (
  59992, 59997, 59998, 59805, 59901, 59944, 52688, 59945, 59946, 59938,
  51789, 60011, 60007, 51790, 53214, 58473, 59860, 59927, 50790, 59818
)
GROUP BY p.id, p.prestamo_id, p.fecha_pago, p.monto_pagado
ORDER BY p.prestamo_id, p.fecha_pago NULLS LAST, p.id;
