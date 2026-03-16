-- =============================================================================
-- ESTADOS DE PAGOS – Consultas SQL
-- =============================================================================
-- Tabla principal: pagos (columna estado VARCHAR(30), nullable).
-- En el código se usan: PENDIENTE (recién creado/sin conciliar), PAGADO (conciliado/aplicado a cuotas).
-- =============================================================================

-- 1) Valores distintos de estado en la tabla pagos
SELECT DISTINCT estado
  FROM pagos
 ORDER BY estado;

-- 2) Conteo por estado (pagos)
SELECT estado,
       COUNT(*) AS cantidad,
       COALESCE(SUM(monto_pagado), 0) AS monto_total
  FROM pagos
 GROUP BY estado
 ORDER BY estado;

-- 3) Pagos con estado NULL (si los hay)
SELECT COUNT(*) AS cantidad_estado_null
  FROM pagos
 WHERE estado IS NULL;

-- 4) Resumen: todos los estados con cantidad y total (incluyendo NULL como 'NULL')
SELECT COALESCE(estado, '(NULL)') AS estado,
       COUNT(*) AS cantidad,
       COALESCE(SUM(monto_pagado), 0) AS monto_total
  FROM pagos
 GROUP BY estado
 ORDER BY estado;

-- =============================================================================
-- Opcional: estados en cuotas (cuotas.estado: PENDIENTE, PAGADO, VENCIDO, MORA, PAGO_ADELANTADO)
-- =============================================================================
-- SELECT estado, COUNT(*) AS cantidad
--   FROM cuotas
--  GROUP BY estado
--  ORDER BY estado;

-- =============================================================================
-- Opcional: estados en pagos_reportados (módulo Cobros: pendiente, aprobado, rechazado, etc.)
-- =============================================================================
-- SELECT estado, COUNT(*) AS cantidad
--   FROM pagos_reportados
--  GROUP BY estado
--  ORDER BY estado;
