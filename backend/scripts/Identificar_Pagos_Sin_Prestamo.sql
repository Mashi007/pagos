-- ============================================================================
-- IDENTIFICAR PAGOS SIN PRESTAMO_ID QUE PUEDEN SER VINCULADOS
-- Ejecutar para ver cuántos pagos pueden vincularse a préstamos
-- ============================================================================

-- PASO 1: Pagos sin prestamo_id que tienen cédula y podrían vincularse
SELECT 
    'PASO 1: Pagos sin prestamo_id que pueden vincularse' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    COUNT(DISTINCT pr.id) AS prestamos_posibles,
    STRING_AGG(pr.id::TEXT, ', ' ORDER BY pr.fecha_aprobacion DESC) AS ids_prestamos,
    CASE 
        WHEN COUNT(DISTINCT pr.id) = 0 THEN 'ERROR: No hay prestamos para esta cedula'
        WHEN COUNT(DISTINCT pr.id) = 1 THEN 'OK: Unico prestamo posible'
        ELSE 'ATENCION: Multiple prestamos - requiere seleccion manual'
    END AS estado_vinculacion
FROM pagos p
LEFT JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
    AND pr.estado = 'APROBADO'
WHERE p.prestamo_id IS NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
ORDER BY 
    CASE 
        WHEN COUNT(DISTINCT pr.id) = 1 THEN 1
        WHEN COUNT(DISTINCT pr.id) > 1 THEN 2
        ELSE 3
    END,
    p.fecha_pago DESC
LIMIT 50;

-- PASO 2: Resumen de pagos sin prestamo_id por tipo de vinculacion
SELECT 
    'PASO 2: Resumen de vinculacion posible' AS seccion;

WITH pagos_con_prestamos AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.monto_pagado,
        COUNT(DISTINCT pr.id) AS cantidad_prestamos
    FROM pagos p
    LEFT JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
        AND pr.estado = 'APROBADO'
    WHERE p.prestamo_id IS NULL
    GROUP BY p.id, p.cedula_cliente, p.monto_pagado
)
SELECT 
    CASE 
        WHEN cantidad_prestamos = 0 THEN 'Sin prestamos disponibles'
        WHEN cantidad_prestamos = 1 THEN 'Unico prestamo (puede vincularse automaticamente)'
        ELSE 'Multiple prestamos (requiere seleccion manual)'
    END AS tipo_vinculacion,
    COUNT(DISTINCT pago_id) AS cantidad_pagos,
    COUNT(DISTINCT cedula_cliente) AS clientes_afectados,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos_con_prestamos
GROUP BY 
    CASE 
        WHEN cantidad_prestamos = 0 THEN 'Sin prestamos disponibles'
        WHEN cantidad_prestamos = 1 THEN 'Unico prestamo (puede vincularse automaticamente)'
        ELSE 'Multiple prestamos (requiere seleccion manual)'
    END
ORDER BY cantidad_pagos DESC;

