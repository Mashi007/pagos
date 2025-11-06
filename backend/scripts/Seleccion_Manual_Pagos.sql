-- ============================================================================
-- SELECCION MANUAL DE PAGOS CON MULTIPLES PRESTAMOS
-- Script para revisar y vincular manualmente los 249 pagos
-- ============================================================================

-- PASO 1: Vista completa de pagos y préstamos disponibles para selección manual
SELECT 
    'PASO 1: Pagos con multiples prestamos - Vista para seleccion manual' AS seccion;

WITH pagos_multiple_prestamo AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.monto_pagado,
        p.fecha_pago,
        p.fecha_registro,
        p.estado AS estado_pago,
        COUNT(DISTINCT pr.id) AS cantidad_prestamos_posibles
    FROM pagos p
    INNER JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
        AND pr.estado = 'APROBADO'
    WHERE p.prestamo_id IS NULL
    GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.fecha_registro, p.estado
    HAVING COUNT(DISTINCT pr.id) > 1
)
SELECT 
    pmp.pago_id,
    pmp.cedula_cliente,
    pmp.monto_pagado,
    TO_CHAR(pmp.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    TO_CHAR(pmp.fecha_registro, 'DD/MM/YYYY HH24:MI') AS fecha_registro_pago,
    pmp.cantidad_prestamos_posibles,
    pr.id AS prestamo_id_disponible,
    pr.total_financiamiento AS monto_prestamo,
    pr.numero_cuotas,
    TO_CHAR(pr.fecha_aprobacion, 'DD/MM/YYYY') AS fecha_aprobacion,
    COUNT(DISTINCT c.id) AS cuotas_prestamo,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COALESCE(SUM(CASE WHEN c.estado = 'PENDIENTE' THEN c.monto_cuota - c.total_pagado ELSE 0 END), 0) AS saldo_pendiente_prestamo,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'SIN CUOTAS'
        WHEN COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) > 0 THEN 'TIENE CUOTAS PENDIENTES'
        ELSE 'TODAS LAS CUOTAS PAGADAS'
    END AS estado_prestamo
FROM pagos_multiple_prestamo pmp
INNER JOIN prestamos pr ON pmp.cedula_cliente = pr.cedula 
    AND pr.estado = 'APROBADO'
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
GROUP BY pmp.pago_id, pmp.cedula_cliente, pmp.monto_pagado, pmp.fecha_pago, pmp.fecha_registro, 
         pmp.cantidad_prestamos_posibles, pr.id, pr.total_financiamiento, pr.numero_cuotas, pr.fecha_aprobacion
ORDER BY pmp.pago_id, pr.fecha_aprobacion DESC
LIMIT 200;

-- PASO 2: Resumen por pago (para facilitar la decisión)
SELECT 
    'PASO 2: Resumen por pago - Facilita la decision' AS seccion;

WITH prestamos_por_cliente AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.total_financiamiento,
        pr.numero_cuotas,
        pr.fecha_aprobacion,
        COUNT(DISTINCT c.id) AS total_cuotas,
        COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
        COALESCE(SUM(CASE WHEN c.estado = 'PENDIENTE' THEN c.monto_cuota - c.total_pagado ELSE 0 END), 0) AS saldo_pendiente
    FROM prestamos pr
    LEFT JOIN cuotas c ON pr.id = c.prestamo_id
    WHERE pr.estado = 'APROBADO'
    GROUP BY pr.cedula, pr.id, pr.total_financiamiento, pr.numero_cuotas, pr.fecha_aprobacion
),
pagos_multiple AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.monto_pagado,
        p.fecha_pago
    FROM pagos p
    WHERE p.prestamo_id IS NULL
        AND EXISTS (
            SELECT 1 
            FROM prestamos pr 
            WHERE pr.cedula = p.cedula_cliente 
                AND pr.estado = 'APROBADO'
            GROUP BY pr.cedula
            HAVING COUNT(DISTINCT pr.id) > 1
        )
)
SELECT 
    pm.pago_id,
    pm.cedula_cliente,
    pm.monto_pagado,
    TO_CHAR(pm.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    STRING_AGG(
        CONCAT('Préstamo ID: ', ppc.prestamo_id::TEXT,
               ' | Monto: $', ppc.total_financiamiento::TEXT,
               ' | Cuotas: ', ppc.total_cuotas::TEXT,
               ' | Pendientes: ', ppc.cuotas_pendientes::TEXT,
               ' | Saldo: $', ppc.saldo_pendiente::TEXT,
               ' | Fecha: ', TO_CHAR(ppc.fecha_aprobacion, 'DD/MM/YYYY')),
        E'\n' ORDER BY ppc.fecha_aprobacion DESC
    ) AS opciones_prestamos
FROM pagos_multiple pm
INNER JOIN prestamos_por_cliente ppc ON pm.cedula_cliente = ppc.cedula
GROUP BY pm.pago_id, pm.cedula_cliente, pm.monto_pagado, pm.fecha_pago
ORDER BY pm.cedula_cliente, pm.fecha_pago DESC;

-- PASO 3: Template para UPDATE manual (copiar y pegar según necesidad)
SELECT 
    'PASO 3: Template para UPDATE manual' AS seccion;

SELECT 
    CONCAT('-- Vincular pago ID ', p.id, ' al prestamo ID [SELECCIONAR_ID]') AS instruccion_update,
    CONCAT('UPDATE pagos SET prestamo_id = [SELECCIONAR_ID] WHERE id = ', p.id, ';') AS codigo_sql,
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    STRING_AGG(pr.id::TEXT, ', ' ORDER BY pr.fecha_aprobacion DESC) AS prestamos_disponibles_ids
FROM pagos p
INNER JOIN prestamos pr ON p.cedula_cliente = pr.cedula 
    AND pr.estado = 'APROBADO'
WHERE p.prestamo_id IS NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado
HAVING COUNT(DISTINCT pr.id) > 1
ORDER BY p.id
LIMIT 50;

