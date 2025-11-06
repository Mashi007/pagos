-- ============================================================================
-- ANALIZAR PAGOS CON MULTIPLES PRESTAMOS POSIBLES
-- Estos 249 pagos requieren selección manual porque el cliente tiene
-- más de un préstamo aprobado
-- ============================================================================

-- PASO 1: Identificar los clientes con múltiples préstamos
SELECT 
    'PASO 1: Clientes con multiples prestamos aprobados' AS seccion;

SELECT 
    p.cedula_cliente,
    COUNT(DISTINCT pr.id) AS cantidad_prestamos,
    STRING_AGG(pr.id::TEXT, ', ' ORDER BY pr.fecha_aprobacion DESC) AS ids_prestamos,
    STRING_AGG(pr.total_financiamiento::TEXT, ', ' ORDER BY pr.fecha_aprobacion DESC) AS montos_prestamos,
    STRING_AGG(TO_CHAR(pr.fecha_aprobacion, 'DD/MM/YYYY'), ', ' ORDER BY pr.fecha_aprobacion DESC) AS fechas_aprobacion,
    COUNT(DISTINCT p.id) AS cantidad_pagos_sin_vinculacion,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado_sin_vinculacion
FROM pagos p
INNER JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
    AND pr.estado = 'APROBADO'
WHERE p.prestamo_id IS NULL
GROUP BY p.cedula_cliente
HAVING COUNT(DISTINCT pr.id) > 1  -- Solo clientes con múltiples préstamos
ORDER BY cantidad_pagos_sin_vinculacion DESC;

-- PASO 2: Detalle de los 249 pagos problemáticos
SELECT 
    'PASO 2: Detalle de los 249 pagos con multiples prestamos posibles' AS seccion;

WITH cantidad_prestamos_cliente AS (
    SELECT 
        cedula,
        COUNT(DISTINCT id) AS cantidad_prestamos
    FROM prestamos
    WHERE estado = 'APROBADO'
    GROUP BY cedula
    HAVING COUNT(DISTINCT id) > 1
),
prestamos_por_cliente AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.total_financiamiento,
        pr.numero_cuotas,
        pr.fecha_aprobacion,
        pr.estado
    FROM prestamos pr
    WHERE pr.estado = 'APROBADO'
)
SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    TO_CHAR(p.fecha_registro, 'DD/MM/YYYY HH24:MI') AS fecha_registro_pago,
    cpc.cantidad_prestamos AS cantidad_prestamos_cliente,
    STRING_AGG(
        CONCAT('ID: ', ppc.prestamo_id::TEXT, 
               ' | Monto: $', ppc.total_financiamiento::TEXT,
               ' | Cuotas: ', ppc.numero_cuotas::TEXT,
               ' | Fecha: ', TO_CHAR(ppc.fecha_aprobacion, 'DD/MM/YYYY')),
        E'\n' ORDER BY ppc.fecha_aprobacion DESC
    ) AS prestamos_disponibles
FROM pagos p
INNER JOIN cantidad_prestamos_cliente cpc ON p.cedula_cliente = cpc.cedula
INNER JOIN prestamos_por_cliente ppc ON p.cedula_cliente = ppc.cedula
WHERE p.prestamo_id IS NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.fecha_registro, cpc.cantidad_prestamos
ORDER BY p.fecha_pago DESC, p.cedula_cliente
LIMIT 50;

-- PASO 3: Resumen por cliente
SELECT 
    'PASO 3: Resumen por cliente (los 4 clientes afectados)' AS seccion;

SELECT 
    p.cedula_cliente,
    COUNT(DISTINCT pr.id) AS total_prestamos_cliente,
    COUNT(DISTINCT p.id) AS total_pagos_sin_vinculacion,
    COALESCE(SUM(p.monto_pagado), 0) AS monto_total_sin_vinculacion,
    STRING_AGG(DISTINCT pr.id::TEXT, ', ' ORDER BY pr.id::TEXT) AS ids_prestamos,
    MIN(p.fecha_pago) AS primer_pago,
    MAX(p.fecha_pago) AS ultimo_pago
FROM pagos p
INNER JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
    AND pr.estado = 'APROBADO'
WHERE p.prestamo_id IS NULL
GROUP BY p.cedula_cliente
HAVING COUNT(DISTINCT pr.id) > 1
ORDER BY total_pagos_sin_vinculacion DESC;

-- PASO 4: Estrategia sugerida para vincular estos pagos
SELECT 
    'PASO 4: Estrategia de vinculacion' AS seccion;

SELECT 
    'OPCION 1: Vincular al prestamo mas reciente' AS estrategia,
    'Usar el prestamo con fecha_aprobacion mas reciente para cada cliente' AS descripcion

UNION ALL

SELECT 
    'OPCION 2: Vincular al prestamo con mayor monto',
    'Usar el prestamo con total_financiamiento mas alto para cada cliente'

UNION ALL

SELECT 
    'OPCION 3: Vincular al prestamo con cuotas pendientes',
    'Vincular al prestamo que tenga cuotas PENDIENTES y que coincida con el monto del pago'

UNION ALL

SELECT 
    'OPCION 4: Seleccion manual',
    'Revisar cada caso individualmente y vincular manualmente segun criterio de negocio';

-- PASO 5: Sugerencia automatica (prestamo mas reciente)
SELECT 
    'PASO 5: Preview vinculacion sugerida (prestamo mas reciente)' AS seccion;

WITH prestamos_por_fecha AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.fecha_aprobacion,
        pr.total_financiamiento,
        ROW_NUMBER() OVER (PARTITION BY pr.cedula ORDER BY pr.fecha_aprobacion DESC) AS rn
    FROM prestamos pr
    WHERE pr.estado = 'APROBADO'
),
clientes_multiple_prestamo AS (
    SELECT cedula
    FROM prestamos
    WHERE estado = 'APROBADO'
    GROUP BY cedula
    HAVING COUNT(DISTINCT id) > 1
)
SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    ppf.prestamo_id AS prestamo_sugerido,
    ppf.fecha_aprobacion AS fecha_aprobacion_prestamo,
    ppf.total_financiamiento AS monto_prestamo,
    COUNT(DISTINCT c.id) AS cuotas_prestamo,
    CASE 
        WHEN COUNT(DISTINCT c.id) > 0 THEN 'OK (Tiene cuotas generadas)'
        ELSE 'ATENCION (Sin cuotas generadas)'
    END AS estado_prestamo
FROM pagos p
INNER JOIN clientes_multiple_prestamo cmp ON p.cedula_cliente = cmp.cedula
INNER JOIN prestamos_por_fecha ppf ON p.cedula_cliente = ppf.cedula AND ppf.rn = 1
LEFT JOIN cuotas c ON ppf.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, ppf.prestamo_id, ppf.fecha_aprobacion, ppf.total_financiamiento
ORDER BY p.cedula_cliente, p.fecha_pago DESC
LIMIT 50;

