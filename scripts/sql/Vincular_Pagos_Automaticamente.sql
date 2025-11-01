-- ============================================================================
-- VINCULAR PAGOS SIN PRESTAMO_ID (SOLO CUANDO HAY UN UNICO PRESTAMO)
-- IMPORTANTE: Ejecutar con precaucion, revisar primero los resultados
-- ============================================================================

-- PASO 1: PREVIEW - Ver qué pagos se vincularían (SOLO LECTURA)
SELECT 
    'PASO 1: PREVIEW - Pagos que se vincularian' AS seccion;

WITH prestamos_unicos AS (
    SELECT 
        cedula,
        id AS prestamo_id,
        estado,
        total_financiamiento,
        fecha_aprobacion
    FROM prestamos
    WHERE estado = 'APROBADO'
),
clientes_con_un_prestamo AS (
    SELECT 
        cedula
    FROM prestamos_unicos
    GROUP BY cedula
    HAVING COUNT(DISTINCT prestamo_id) = 1
)
SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    pu.prestamo_id AS prestamo_id_vinculado,
    pu.estado AS estado_prestamo,
    pu.total_financiamiento,
    TO_CHAR(pu.fecha_aprobacion, 'DD/MM/YYYY') AS fecha_aprobacion,
    COUNT(DISTINCT c.id) AS cuotas_prestamo
FROM pagos p
INNER JOIN clientes_con_un_prestamo cunp ON p.cedula_cliente = cunp.cedula
INNER JOIN prestamos_unicos pu ON p.cedula_cliente = pu.cedula
LEFT JOIN cuotas c ON pu.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, pu.prestamo_id, pu.estado, pu.total_financiamiento, pu.fecha_aprobacion
ORDER BY p.fecha_pago DESC
LIMIT 100;

-- PASO 2: CONTEO - Cuántos pagos se vincularían
SELECT 
    'PASO 2: Resumen de vinculacion' AS seccion;

WITH prestamos_por_cliente AS (
    SELECT 
        cedula,
        COUNT(DISTINCT id) AS cantidad_prestamos,
        MAX(id) AS prestamo_id_unico
    FROM prestamos
    WHERE estado = 'APROBADO'
    GROUP BY cedula
    HAVING COUNT(DISTINCT id) = 1  -- Solo clientes con UN unico prestamo
)
SELECT 
    COUNT(DISTINCT p.id) AS pagos_que_se_vincularian,
    COUNT(DISTINCT p.cedula_cliente) AS clientes_afectados,
    COALESCE(SUM(p.monto_pagado), 0) AS monto_total
FROM pagos p
INNER JOIN prestamos_por_cliente ppc ON p.cedula_cliente = ppc.cedula
WHERE p.prestamo_id IS NULL;

-- ============================================================================
-- PASO 3: ACTUALIZAR PAGOS (COMENTADO POR SEGURIDAD - DESCOMENTAR PARA EJECUTAR)
-- ============================================================================

-- ACTUALIZAR pagos que tienen un UNICO prestamo posible
WITH prestamos_unicos AS (
    SELECT 
        cedula,
        id AS prestamo_id,
        estado
    FROM prestamos
    WHERE estado = 'APROBADO'
),
clientes_con_un_prestamo AS (
    SELECT 
        cedula
    FROM prestamos_unicos
    GROUP BY cedula
    HAVING COUNT(DISTINCT prestamo_id) = 1
)
UPDATE pagos p
SET prestamo_id = (
    SELECT pu.prestamo_id
    FROM prestamos_unicos pu
    INNER JOIN clientes_con_un_prestamo cunp ON pu.cedula = cunp.cedula
    WHERE pu.cedula = p.cedula_cliente
    LIMIT 1
)
WHERE p.prestamo_id IS NULL
    AND p.cedula_cliente IN (
        SELECT cedula FROM clientes_con_un_prestamo
    );

-- Verificar resultado
SELECT 
    'PASO 4: Verificacion despues de actualizar' AS seccion;

SELECT 
    COUNT(*) AS total_pagos_con_prestamo_id,
    COUNT(DISTINCT prestamo_id) AS prestamos_vinculados,
    COUNT(DISTINCT cedula_cliente) AS clientes_con_pagos_vinculados
FROM pagos
WHERE prestamo_id IS NOT NULL;

SELECT 
    COUNT(*) AS pagos_sin_prestamo_id_restantes
FROM pagos
WHERE prestamo_id IS NULL;

