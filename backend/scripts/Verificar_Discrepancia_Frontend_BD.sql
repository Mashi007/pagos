-- ============================================================================
-- VERIFICAR DISCREPANCIA ENTRE BASE DE DATOS Y FRONTEND
-- El frontend muestra todo como "Pendiente" pero BD debería tener cuotas pagadas
-- ============================================================================

-- PASO 1: Verificar préstamos que SÍ tienen pagos aplicados
SELECT 
    'PASO 1: Prestamos con pagos aplicados' AS seccion;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    LEFT(p.nombres, 30) AS cliente,
    COUNT(DISTINCT pag.id) AS total_pagos,
    COALESCE(SUM(pag.monto_pagado), 0) AS monto_total_pagado,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago
FROM prestamos p
INNER JOIN pagos pag ON p.id = pag.prestamo_id
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE pag.prestamo_id IS NOT NULL
    AND pag.monto_pagado > 0
GROUP BY p.id, p.cedula, p.nombres
HAVING COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) > 0
ORDER BY cuotas_pagadas DESC
LIMIT 10;

-- PASO 2: Ver detalle de cuotas PAGADAS en la BD
SELECT 
    'PASO 2: Ejemplo de cuotas PAGADAS en BD' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.estado AS estado_bd,
    TO_CHAR(c.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    p.cedula,
    LEFT(p.nombres, 30) AS cliente
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado = 'PAGADO'
    AND c.total_pagado > 0
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- PASO 3: Verificar si el problema es solo con préstamo #61 o es general
SELECT 
    'PASO 3: Resumen general de estados' AS seccion;

SELECT 
    c.estado AS estado_cuota,
    COUNT(*) AS cantidad_cuotas,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_afectados,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado,
    COALESCE(SUM(c.monto_cuota), 0) AS monto_total_cuotas
FROM cuotas c
GROUP BY c.estado
ORDER BY cantidad_cuotas DESC;

-- PASO 4: Verificar un préstamo específico que DEBERÍA tener cuotas pagadas
-- Buscar el primer préstamo con cuotas PAGADAS
SELECT 
    'PASO 4: Verificar prestamo con cuotas pagadas' AS seccion;

WITH prestamos_con_pagos AS (
    SELECT 
        c.prestamo_id,
        COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas
    FROM cuotas c
    WHERE c.estado = 'PAGADO'
    GROUP BY c.prestamo_id
    ORDER BY cuotas_pagadas DESC
    LIMIT 1
)
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres AS cliente,
    p.total_financiamiento,
    p.numero_cuotas,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas_bd,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes_bd,
    COUNT(DISTINCT pag.id) AS pagos_registrados
FROM prestamos p
INNER JOIN prestamos_con_pagos pcp ON p.id = pcp.prestamo_id
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN pagos pag ON p.id = pag.prestamo_id
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento, p.numero_cuotas;

-- PASO 5: Verificar si hay pagos sin aplicar (pendientes de procesar)
SELECT 
    'PASO 5: Pagos que podrian no haberse aplicado' AS seccion;

WITH pagos_resumen AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado,
        COALESCE(SUM(c.total_pagado), 0) AS total_aplicado
    FROM pagos p
    LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
    WHERE p.prestamo_id IS NOT NULL
        AND p.monto_pagado > 0
    GROUP BY p.id, p.prestamo_id, p.monto_pagado
)
SELECT 
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN total_aplicado >= monto_pagado THEN 1 END) AS pagos_aplicados_completos,
    COUNT(CASE WHEN total_aplicado > 0 AND total_aplicado < monto_pagado THEN 1 END) AS pagos_aplicados_parciales,
    COUNT(CASE WHEN total_aplicado = 0 THEN 1 END) AS pagos_sin_aplicar,
    COALESCE(SUM(monto_pagado), 0) AS monto_total_pagado,
    COALESCE(SUM(total_aplicado), 0) AS monto_total_aplicado,
    COALESCE(SUM(monto_pagado - total_aplicado), 0) AS diferencia_pendiente
FROM pagos_resumen;

-- PASO 6: Verificar si el problema está en la fecha_pago o en el estado
SELECT 
    'PASO 6: Analizar campos fecha_pago y estado' AS seccion;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS estado_pagado,
    COUNT(CASE WHEN total_pagado >= monto_cuota THEN 1 END) AS deberia_estar_pagado,
    COUNT(CASE WHEN estado = 'PAGADO' AND total_pagado >= monto_cuota THEN 1 END) AS correctamente_pagado,
    COUNT(CASE WHEN total_pagado >= monto_cuota AND estado != 'PAGADO' THEN 1 END) AS inconsistencia_estado,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS tiene_fecha_pago,
    COUNT(CASE WHEN estado = 'PAGADO' AND fecha_pago IS NULL THEN 1 END) AS pagado_sin_fecha
FROM cuotas;

