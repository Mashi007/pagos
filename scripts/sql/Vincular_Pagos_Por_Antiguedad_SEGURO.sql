-- ============================================================================
-- VINCULAR PAGOS AUTOMATICAMENTE POR ANTIGÜEDAD - VERSION SEGURA
-- Lógica: Si tenemos claro el número de cédula (IDENTICA), cargar los montos 
--         en orden ir cubriendo desde el préstamo más antiguo
-- IMPORTANTE: Solo vincula cuando cedula_cliente del pago = cedula del préstamo
--             (comparación exacta, case-sensitive)
-- ============================================================================

-- PASO 1: PREVIEW - Ver cómo se vincularían los pagos (con verificación de cédula)
SELECT 
    'PASO 1: PREVIEW - Vinculacion por antiguedad (cedula IDENTICA)' AS seccion;

WITH prestamos_ordenados AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.fecha_aprobacion,
        pr.total_financiamiento,
        pr.numero_cuotas,
        ROW_NUMBER() OVER (PARTITION BY pr.cedula ORDER BY pr.fecha_aprobacion ASC, pr.id ASC) AS orden_antiguedad,
        COUNT(*) OVER (PARTITION BY pr.cedula) AS total_prestamos_cliente
    FROM prestamos pr
    WHERE pr.estado = 'APROBADO'
),
pagos_ordenados AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.monto_pagado,
        p.fecha_pago,
        ROW_NUMBER() OVER (PARTITION BY p.cedula_cliente ORDER BY p.fecha_pago ASC, p.id ASC) AS orden_pago
    FROM pagos p
    WHERE p.prestamo_id IS NULL
        AND EXISTS (
            SELECT 1 
            FROM prestamos pr 
            WHERE pr.cedula = p.cedula_cliente  -- COMPARACION EXACTA
                AND pr.estado = 'APROBADO'
            GROUP BY pr.cedula
            HAVING COUNT(DISTINCT pr.id) > 1
        )
),
asignacion_preliminar AS (
    SELECT 
        po.pago_id,
        po.cedula_cliente,
        po.monto_pagado,
        TO_CHAR(po.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
        po.orden_pago,
        pr.prestamo_id,
        pr.fecha_aprobacion,
        pr.total_financiamiento,
        pr.orden_antiguedad,
        pr.total_prestamos_cliente,
        CASE 
            WHEN po.cedula_cliente = pr.cedula  -- VERIFICACION EXACTA DE CEDULA
                AND (po.orden_pago - 1) % pr.total_prestamos_cliente + 1 = pr.orden_antiguedad 
            THEN pr.prestamo_id
            ELSE NULL
        END AS prestamo_id_correcto
    FROM pagos_ordenados po
    INNER JOIN prestamos_ordenados pr ON po.cedula_cliente = pr.cedula  -- JOIN EXACTO
)
SELECT 
    ap.pago_id,
    ap.cedula_cliente,
    ap.monto_pagado,
    ap.fecha_pago,
    ap.orden_pago,
    ap.prestamo_id_correcto AS prestamo_id_asignado,
    TO_CHAR(ap.fecha_aprobacion, 'DD/MM/YYYY') AS fecha_aprobacion_prestamo,
    ap.total_financiamiento AS monto_prestamo,
    ap.orden_antiguedad AS orden_prestamo,
    COUNT(DISTINCT c.id) AS cuotas_prestamo,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    CASE 
        WHEN ap.prestamo_id_correcto IS NOT NULL THEN 'OK (Cedula identica, asignacion correcta)'
        ELSE 'ERROR (Cedula no coincide)'
    END AS validacion
FROM asignacion_preliminar ap
LEFT JOIN cuotas c ON ap.prestamo_id_correcto = c.prestamo_id
WHERE ap.prestamo_id_correcto IS NOT NULL  -- Solo mostrar asignaciones válidas
GROUP BY ap.pago_id, ap.cedula_cliente, ap.monto_pagado, ap.fecha_pago, ap.orden_pago, 
         ap.prestamo_id_correcto, ap.fecha_aprobacion, ap.total_financiamiento, ap.orden_antiguedad, ap.total_prestamos_cliente
ORDER BY ap.cedula_cliente, ap.fecha_pago ASC, ap.orden_pago
LIMIT 100;

-- PASO 2: Verificar cédulas que NO coinciden exactamente (posibles problemas)
SELECT 
    'PASO 2: Verificar posibles problemas de cédulas' AS seccion;

SELECT 
    'Pagos sin prestamo_id que tienen cédula similar pero no identica' AS tipo_verificacion,
    COUNT(DISTINCT p.id) AS cantidad_pagos
FROM pagos p
WHERE p.prestamo_id IS NULL
    AND NOT EXISTS (
        SELECT 1 
        FROM prestamos pr 
        WHERE pr.cedula = p.cedula_cliente  -- Comparacion exacta
            AND pr.estado = 'APROBADO'
    )
    AND EXISTS (
        SELECT 1 
        FROM prestamos pr 
        WHERE UPPER(TRIM(pr.cedula)) = UPPER(TRIM(p.cedula_cliente))  -- Similar pero no identica
            AND pr.estado = 'APROBADO'
    );

-- PASO 3: Resumen de asignaciones (solo cédulas IDENTICAS)
SELECT 
    'PASO 3: Resumen de asignaciones (cedulas IDENTICAS)' AS seccion;

WITH prestamos_ordenados AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.fecha_aprobacion,
        ROW_NUMBER() OVER (PARTITION BY pr.cedula ORDER BY pr.fecha_aprobacion ASC, pr.id ASC) AS orden_antiguedad,
        COUNT(*) OVER (PARTITION BY pr.cedula) AS total_prestamos_cliente
    FROM prestamos pr
    WHERE pr.estado = 'APROBADO'
),
pagos_ordenados AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.monto_pagado,
        p.fecha_pago,
        ROW_NUMBER() OVER (PARTITION BY p.cedula_cliente ORDER BY p.fecha_pago ASC, p.id ASC) AS orden_pago
    FROM pagos p
    WHERE p.prestamo_id IS NULL
        AND EXISTS (
            SELECT 1 
            FROM prestamos pr 
            WHERE pr.cedula = p.cedula_cliente  -- COMPARACION EXACTA
                AND pr.estado = 'APROBADO'
            GROUP BY pr.cedula
            HAVING COUNT(DISTINCT pr.id) > 1
        )
),
asignacion_final AS (
    SELECT 
        po.pago_id,
        po.cedula_cliente,
        po.orden_pago,
        pr.prestamo_id,
        pr.orden_antiguedad,
        pr.total_prestamos_cliente
    FROM pagos_ordenados po
    INNER JOIN prestamos_ordenados pr ON po.cedula_cliente = pr.cedula  -- JOIN EXACTO
    WHERE (po.orden_pago - 1) % pr.total_prestamos_cliente + 1 = pr.orden_antiguedad
)
SELECT 
    COUNT(DISTINCT af.pago_id) AS total_pagos_a_actualizar,
    COUNT(DISTINCT af.cedula_cliente) AS clientes_afectados,
    COUNT(DISTINCT af.prestamo_id) AS prestamos_vinculados,
    COALESCE(SUM(p.monto_pagado), 0) AS monto_total
FROM asignacion_final af
INNER JOIN pagos p ON af.pago_id = p.id;

-- ============================================================================
-- PASO 4: ACTUALIZAR PAGOS (SOLO SI CEDULA ES IDENTICA)
-- ============================================================================

WITH prestamos_ordenados AS (
    SELECT 
        pr.cedula,
        pr.id AS prestamo_id,
        pr.fecha_aprobacion,
        ROW_NUMBER() OVER (PARTITION BY pr.cedula ORDER BY pr.fecha_aprobacion ASC, pr.id ASC) AS orden_antiguedad,
        COUNT(*) OVER (PARTITION BY pr.cedula) AS total_prestamos_cliente
    FROM prestamos pr
    WHERE pr.estado = 'APROBADO'
),
pagos_ordenados AS (
    SELECT 
        p.id AS pago_id,
        p.cedula_cliente,
        p.fecha_pago,
        ROW_NUMBER() OVER (PARTITION BY p.cedula_cliente ORDER BY p.fecha_pago ASC, p.id ASC) AS orden_pago
    FROM pagos p
    WHERE p.prestamo_id IS NULL
        AND EXISTS (
            SELECT 1 
            FROM prestamos pr 
            WHERE pr.cedula = p.cedula_cliente  -- COMPARACION EXACTA
                AND pr.estado = 'APROBADO'
            GROUP BY pr.cedula
            HAVING COUNT(DISTINCT pr.id) > 1
        )
),
asignacion_final AS (
    SELECT 
        po.pago_id,
        pr.prestamo_id
    FROM pagos_ordenados po
    INNER JOIN prestamos_ordenados pr ON po.cedula_cliente = pr.cedula  -- JOIN EXACTO (cedula identica)
    WHERE (po.orden_pago - 1) % pr.total_prestamos_cliente + 1 = pr.orden_antiguedad
        AND po.cedula_cliente = pr.cedula  -- DOBLE VERIFICACION: cedula identica
)
UPDATE pagos p
SET prestamo_id = af.prestamo_id
FROM asignacion_final af
WHERE p.id = af.pago_id
    AND p.cedula_cliente = (SELECT cedula FROM prestamos WHERE id = af.prestamo_id);  -- TRIPLE VERIFICACION: cedula identica

-- ============================================================================
-- PASO 5: Verificar resultados
-- ============================================================================

SELECT 
    'PASO 5: Verificacion despues de actualizar' AS seccion;

-- Verificar que todas las vinculaciones tienen cédulas idénticas
SELECT 
    COUNT(*) AS total_vinculaciones,
    COUNT(CASE WHEN p.cedula_cliente = pr.cedula THEN 1 END) AS vinculaciones_cedula_identica,
    COUNT(CASE WHEN p.cedula_cliente != pr.cedula THEN 1 END) AS errores_cedula_diferente
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL
    AND EXISTS (
        SELECT 1 
        FROM prestamos pr2 
        WHERE pr2.cedula = p.cedula_cliente 
            AND pr2.estado = 'APROBADO'
        GROUP BY pr2.cedula
        HAVING COUNT(DISTINCT pr2.id) > 1
    );

-- Verificar cuántos quedan sin vincular
SELECT 
    COUNT(*) AS pagos_sin_vinculacion_restantes
FROM pagos
WHERE prestamo_id IS NULL
    AND EXISTS (
        SELECT 1 
        FROM prestamos pr 
        WHERE pr.cedula = pagos.cedula_cliente  -- Comparacion exacta
            AND pr.estado = 'APROBADO'
        GROUP BY pr.cedula
        HAVING COUNT(DISTINCT pr.id) > 1
    );

