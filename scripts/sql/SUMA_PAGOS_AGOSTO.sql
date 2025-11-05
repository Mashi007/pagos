-- ============================================================================
-- SCRIPT: SUMA DE MONTO_PAGADO EN TODO EL MES DE AGOSTO
-- ============================================================================
-- Descripción: Calcula el total de pagos realizados durante el mes de agosto
--              Consulta las tablas 'pagos' y 'pagos_staging'
--
-- Uso: 
--   1. Modificar el año en las variables @AÑO (o usar directamente en las fechas)
--   2. Ejecutar todo el script en DBeaver
--   3. Revisar los resultados en las 3 consultas
--
-- Autor: Sistema de Pagos
-- Fecha: 2024
-- ============================================================================

-- ============================================================================
-- CONFIGURACIÓN: Cambiar el año aquí
-- ============================================================================
-- Por defecto: año actual (2024). Cambiar según necesidad.
-- Para cambiar el año, modifica las fechas en las consultas siguientes.

-- ============================================================================
-- 1. SUMA DE PAGOS - TABLA 'pagos'
-- ============================================================================
-- Suma los pagos de la tabla oficial 'pagos' para el mes de agosto
SELECT 
    'PAGOS (tabla oficial)' AS tabla,
    COUNT(*) AS cantidad_registros,
    COALESCE(SUM(monto_pagado), 0) AS total_monto_pagado,
    TO_CHAR(COALESCE(SUM(monto_pagado), 0), 'FM$999,999,999,990.00') AS total_formateado,
    MIN(fecha_pago) AS fecha_minima,
    MAX(fecha_pago) AS fecha_maxima
FROM pagos
WHERE fecha_pago >= '2024-08-01 00:00:00'::timestamp
  AND fecha_pago <= '2024-08-31 23:59:59'::timestamp
  AND activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0;

-- ============================================================================
-- 2. SUMA DE PAGOS - TABLA 'pagos_staging'
-- ============================================================================
-- Suma los pagos de la tabla staging 'pagos_staging' para el mes de agosto
-- Nota: Esta tabla tiene campos TEXT que deben convertirse a tipos numéricos
SELECT 
    'PAGOS_STAGING (tabla temporal)' AS tabla,
    COUNT(*) AS cantidad_registros,
    COALESCE(SUM(monto_pagado::numeric), 0) AS total_monto_pagado,
    TO_CHAR(COALESCE(SUM(monto_pagado::numeric), 0), 'FM$999,999,999,990.00') AS total_formateado,
    MIN(fecha_pago::timestamp) AS fecha_minima,
    MAX(fecha_pago::timestamp) AS fecha_maxima
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
  AND fecha_pago != ''
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}'  -- Validar formato de fecha
  AND fecha_pago::timestamp >= '2024-08-01 00:00:00'::timestamp
  AND fecha_pago::timestamp <= '2024-08-31 23:59:59'::timestamp
  AND monto_pagado IS NOT NULL
  AND monto_pagado != ''
  AND TRIM(monto_pagado) != ''
  AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'  -- Validar formato numérico
  AND monto_pagado::numeric > 0;

-- ============================================================================
-- 3. TOTAL COMBINADO - AMBAS TABLAS
-- ============================================================================
-- Suma total combinando ambas tablas
WITH 
pagos_tabla AS (
    SELECT 
        COALESCE(SUM(monto_pagado), 0) AS total,
        COUNT(*) AS cantidad
    FROM pagos
    WHERE fecha_pago >= '2024-08-01 00:00:00'::timestamp
      AND fecha_pago <= '2024-08-31 23:59:59'::timestamp
      AND activo = TRUE
      AND monto_pagado IS NOT NULL
      AND monto_pagado > 0
),
pagos_staging_tabla AS (
    SELECT 
        COALESCE(SUM(monto_pagado::numeric), 0) AS total,
        COUNT(*) AS cantidad
    FROM pagos_staging
    WHERE fecha_pago IS NOT NULL
      AND fecha_pago != ''
      AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}'
      AND fecha_pago::timestamp >= '2024-08-01 00:00:00'::timestamp
      AND fecha_pago::timestamp <= '2024-08-31 23:59:59'::timestamp
      AND monto_pagado IS NOT NULL
      AND monto_pagado != ''
      AND TRIM(monto_pagado) != ''
      AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
      AND monto_pagado::numeric > 0
)
SELECT 
    'TOTAL COMBINADO' AS resumen,
    (SELECT cantidad FROM pagos_tabla) AS cantidad_pagos,
    (SELECT cantidad FROM pagos_staging_tabla) AS cantidad_pagos_staging,
    (SELECT cantidad FROM pagos_tabla) + (SELECT cantidad FROM pagos_staging_tabla) AS total_registros,
    (SELECT total FROM pagos_tabla) AS total_pagos,
    (SELECT total FROM pagos_staging_tabla) AS total_pagos_staging,
    (SELECT total FROM pagos_tabla) + (SELECT total FROM pagos_staging_tabla) AS total_combinado,
    TO_CHAR(
        (SELECT total FROM pagos_tabla) + (SELECT total FROM pagos_staging_tabla), 
        'FM$999,999,999,990.00'
    ) AS total_combinado_formateado;

-- ============================================================================
-- 4. DESGLOSE DIARIO (OPCIONAL) - Ver pagos por día en agosto
-- ============================================================================
-- Descomenta las siguientes líneas si quieres ver el desglose día por día
/*
SELECT 
    DATE(fecha_pago) AS fecha,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_dia,
    TO_CHAR(COALESCE(SUM(monto_pagado), 0), 'FM$999,999,999,990.00') AS total_dia_formateado
FROM pagos
WHERE fecha_pago >= '2024-08-01 00:00:00'::timestamp
  AND fecha_pago <= '2024-08-31 23:59:59'::timestamp
  AND activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
GROUP BY DATE(fecha_pago)
ORDER BY fecha;

UNION ALL

SELECT 
    DATE(fecha_pago::timestamp) AS fecha,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado::numeric), 0) AS total_dia,
    TO_CHAR(COALESCE(SUM(monto_pagado::numeric), 0), 'FM$999,999,999,990.00') AS total_dia_formateado
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
  AND fecha_pago != ''
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}'
  AND fecha_pago::timestamp >= '2024-08-01 00:00:00'::timestamp
  AND fecha_pago::timestamp <= '2024-08-31 23:59:59'::timestamp
  AND monto_pagado IS NOT NULL
  AND monto_pagado != ''
  AND TRIM(monto_pagado) != ''
  AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
  AND monto_pagado::numeric > 0
GROUP BY DATE(fecha_pago::timestamp)
ORDER BY fecha;
*/

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

