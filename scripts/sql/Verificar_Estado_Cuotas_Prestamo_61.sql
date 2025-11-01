-- ============================================================================
-- VERIFICAR ESTADO DE CUOTAS DEL PRESTAMO #61
-- Verificar si los pagos afectaron correctamente las cuotas
-- ============================================================================

-- PASO 1: Información general del préstamo #61
SELECT 
    'PASO 1: Informacion del prestamo #61' AS seccion;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres AS cliente,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado AS estado_prestamo,
    p.fecha_aprobacion,
    COUNT(DISTINCT c.id) AS total_cuotas_generadas,
    COUNT(DISTINCT pag.id) AS total_pagos_registrados
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN pagos pag ON p.id = pag.prestamo_id
WHERE p.id = 61
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento, p.numero_cuotas, p.estado, p.fecha_aprobacion;

-- PASO 2: Estado actual de TODAS las cuotas del préstamo #61
SELECT 
    'PASO 2: Estado actual de todas las cuotas' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado,
    TO_CHAR(c.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'COMPLETAMENTE PAGADA'
        WHEN c.total_pagado > 0 THEN 'PARCIALMENTE PAGADA'
        ELSE 'SIN PAGO'
    END AS estado_detallado
FROM cuotas c
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota ASC;

-- PASO 3: Pagos registrados para el préstamo #61
SELECT 
    'PASO 3: Pagos registrados para prestamo #61' AS seccion;

SELECT 
    pag.id AS pago_id,
    TO_CHAR(pag.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    pag.monto_pagado,
    pag.cedula_cliente,
    pag.numero_documento,
    TO_CHAR(pag.fecha_registro, 'DD/MM/YYYY HH24:MI') AS fecha_registro
FROM pagos pag
WHERE pag.prestamo_id = 61
ORDER BY pag.fecha_pago ASC, pag.id ASC;

-- PASO 4: Resumen de aplicación de pagos
SELECT 
    'PASO 4: Resumen de aplicacion de pagos' AS seccion;

SELECT 
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    COUNT(DISTINCT CASE WHEN c.estado = 'ATRASADO' THEN c.id END) AS cuotas_atrasadas,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_algun_pago,
    COUNT(DISTINCT CASE WHEN c.total_pagado >= c.monto_cuota THEN c.id END) AS cuotas_completamente_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado_registrado,
    COALESCE(SUM(c.monto_cuota), 0) AS total_deberia_ser,
    COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) AS saldo_pendiente
FROM cuotas c
LEFT JOIN pagos pag ON c.prestamo_id = pag.prestamo_id
WHERE c.prestamo_id = 61;

-- PASO 5: Verificar relación pagos-cuotas (tabla pago_cuotas si existe)
SELECT 
    'PASO 5: Relacion pagos-cuotas (tabla pago_cuotas)' AS seccion;

-- Verificar si existe la tabla de relación
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'pago_cuotas'
        ) THEN 'Tabla pago_cuotas existe'
        ELSE 'Tabla pago_cuotas NO existe'
    END AS estado_tabla_relacion;

-- Si existe, mostrar las relaciones
SELECT 
    pc.pago_id,
    pc.cuota_id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.estado
FROM pago_cuotas pc
INNER JOIN cuotas c ON pc.cuota_id = c.id
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota ASC;

-- PASO 6: Comparar monto_pagado vs total aplicado
SELECT 
    'PASO 6: Comparacion monto pagado vs aplicado' AS seccion;

WITH resumen AS (
    SELECT 
        COALESCE(SUM(pag.monto_pagado), 0) AS total_monto_pagado,
        COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas
    FROM prestamos p
    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.id = 61
)
SELECT 
    total_monto_pagado,
    total_aplicado_cuotas,
    total_monto_pagado - total_aplicado_cuotas AS diferencia,
    CASE 
        WHEN total_aplicado_cuotas >= total_monto_pagado THEN 'OK - Aplicado correctamente'
        WHEN total_aplicado_cuotas > 0 THEN 'PARCIAL - Falta aplicar'
        ELSE 'ERROR - No se aplico nada'
    END AS estado
FROM resumen;

