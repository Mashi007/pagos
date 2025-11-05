-- ============================================================================
-- CÁLCULO DE MOROSIDAD PARA KPIs
-- ============================================================================
-- Este script calcula:
-- 1. Días de morosidad por persona (fecha_pago vs fecha_vencimiento)
-- 2. Dinero no cobrado por mes (monto_cuota_programado vs monto_pagado)
-- ============================================================================

-- ============================================================================
-- CONFIGURACIÓN: CAMBIAR EL MES AQUÍ
-- ============================================================================
-- Cambia el año y mes según necesites
-- Ejemplo: Para Noviembre 2024 usar: año = 2024, mes = 11
DO $$
DECLARE
    año_mes INTEGER := 202411;  -- Cambiar aquí: YYYYMM (ej: 202411 para Nov 2024)
    fecha_inicio DATE;
    fecha_fin DATE;
BEGIN
    -- Convertir YYYYMM a fechas
    fecha_inicio := TO_DATE(año_mes::text, 'YYYYMM');
    fecha_fin := fecha_inicio + INTERVAL '1 month' - INTERVAL '1 day';
    
    RAISE NOTICE 'Calculando morosidad para: % a %', fecha_inicio, fecha_fin;
END $$;

-- ============================================================================
-- 1. DÍAS DE MOROSIDAD POR PERSONA (CLIENTE)
-- ============================================================================
-- Calcula cuántos días de mora tiene cada cliente
-- Compara fecha_pago (de pagos) vs fecha_vencimiento (de cuotas)
-- ============================================================================
WITH pagos_con_cuotas AS (
    SELECT 
        p.cedula,
        p.id AS pago_id,
        p.fecha_pago AS fecha_pago_pago,
        p.monto_pagado,
        p.prestamo_id,
        p.numero_cuota,
        c.id AS cuota_id,
        c.fecha_vencimiento,
        c.monto_cuota,
        c.numero_cuota AS numero_cuota_cuota,
        -- Calcular días de mora
        CASE 
            WHEN p.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL 
                 AND p.fecha_pago::date > c.fecha_vencimiento THEN
                (p.fecha_pago::date - c.fecha_vencimiento)::INTEGER
            ELSE 0
        END AS dias_mora
    FROM pagos p
    INNER JOIN prestamos pr ON p.prestamo_id = pr.id
    LEFT JOIN cuotas c ON (
        c.prestamo_id = p.prestamo_id 
        AND (p.numero_cuota IS NULL OR c.numero_cuota = p.numero_cuota)
    )
    WHERE p.activo = TRUE
      AND p.fecha_pago IS NOT NULL
      AND c.fecha_vencimiento IS NOT NULL
)
SELECT 
    '=== DÍAS DE MOROSIDAD POR PERSONA ===' AS tipo_calculo,
    cedula,
    COUNT(DISTINCT pago_id) AS total_pagos,
    MAX(dias_mora) AS max_dias_mora,
    AVG(dias_mora)::NUMERIC(10,2) AS promedio_dias_mora,
    SUM(CASE WHEN dias_mora > 0 THEN dias_mora ELSE 0 END) AS total_dias_mora_acumulados,
    COUNT(*) FILTER (WHERE dias_mora > 0) AS pagos_con_mora
FROM pagos_con_cuotas
GROUP BY cedula
HAVING MAX(dias_mora) > 0  -- Solo mostrar clientes con mora
ORDER BY max_dias_mora DESC, total_dias_mora_acumulados DESC;

-- ============================================================================
-- 2. DÍAS DE MOROSIDAD POR PERSONA (POR MES)
-- ============================================================================
-- Agrupa por mes y persona para ver la evolución
-- ============================================================================
WITH pagos_con_cuotas AS (
    SELECT 
        p.cedula,
        p.fecha_pago::date AS fecha_pago,
        DATE_TRUNC('month', p.fecha_pago::date) AS mes_pago,
        c.fecha_vencimiento,
        CASE 
            WHEN p.fecha_pago::date > c.fecha_vencimiento THEN
                (p.fecha_pago::date - c.fecha_vencimiento)::INTEGER
            ELSE 0
        END AS dias_mora
    FROM pagos p
    INNER JOIN prestamos pr ON p.prestamo_id = pr.id
    LEFT JOIN cuotas c ON (
        c.prestamo_id = p.prestamo_id 
        AND (p.numero_cuota IS NULL OR c.numero_cuota = p.numero_cuota)
    )
    WHERE p.activo = TRUE
      AND p.fecha_pago IS NOT NULL
      AND c.fecha_vencimiento IS NOT NULL
)
SELECT 
    '=== DÍAS DE MOROSIDAD POR PERSONA Y MES ===' AS tipo_calculo,
    TO_CHAR(mes_pago, 'YYYY-MM') AS mes,
    cedula,
    COUNT(*) AS total_pagos,
    MAX(dias_mora) AS max_dias_mora,
    AVG(dias_mora)::NUMERIC(10,2) AS promedio_dias_mora,
    SUM(dias_mora) AS total_dias_mora
FROM pagos_con_cuotas
WHERE dias_mora > 0
GROUP BY mes_pago, cedula
ORDER BY mes_pago DESC, total_dias_mora DESC;

-- ============================================================================
-- 3. DINERO NO COBRADO POR MES (monto_cuota vs monto_pagado)
-- ============================================================================
-- Calcula cuánto dinero se dejó de cobrar comparando:
-- - monto_cuota (programado) de la tabla de amortización
-- - monto_pagado (real) de la tabla de pagos
-- Agrupado por mes de vencimiento de la cuota
-- ============================================================================
WITH cuotas_vencidas AS (
    SELECT 
        c.id AS cuota_id,
        c.prestamo_id,
        c.numero_cuota,
        c.fecha_vencimiento,
        DATE_TRUNC('month', c.fecha_vencimiento) AS mes_vencimiento,
        c.monto_cuota AS monto_programado,
        c.estado,
        pr.cedula
    FROM cuotas c
    INNER JOIN prestamos pr ON c.prestamo_id = pr.id
    WHERE pr.estado = 'APROBADO'
      AND c.fecha_vencimiento < CURRENT_DATE  -- Solo cuotas vencidas
      AND c.estado != 'PAGADO'  -- Solo cuotas no pagadas completamente
),
pagos_por_mes_vencimiento AS (
    -- Sumar TODOS los monto_pagado de la tabla pagos
    -- IMPORTANTE: Usa el campo monto_pagado directamente de la tabla pagos
    -- ARTICULACIÓN: Si el pago no tiene prestamo_id, busca préstamos por cedula
    SELECT 
        COALESCE(
            DATE_TRUNC('month', c.fecha_vencimiento),
            DATE_TRUNC('month', p.fecha_pago::date)
        ) AS mes_vencimiento,
        COALESCE(SUM(p.monto_pagado), 0) AS monto_pagado_real
    FROM pagos p
    -- ARTICULACIÓN: Si tiene prestamo_id, usar ese. Si no, buscar por cedula
    LEFT JOIN prestamos pr ON (
        -- Caso 1: Pago tiene prestamo_id directo
        (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
        -- Caso 2: Pago NO tiene prestamo_id, buscar por cedula
        OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
    )
    LEFT JOIN cuotas c ON (
        -- Solo relacionar con cuotas si encontramos un préstamo
        pr.id IS NOT NULL
        AND c.prestamo_id = pr.id 
        AND (
            -- Si el pago tiene numero_cuota, usar esa cuota específica
            (p.numero_cuota IS NOT NULL AND c.numero_cuota = p.numero_cuota)
            -- Si no tiene numero_cuota, relacionar con la primera cuota vencida del préstamo en ese mes
            OR (p.numero_cuota IS NULL 
                AND c.fecha_vencimiento = (
                    SELECT MIN(c2.fecha_vencimiento)
                    FROM cuotas c2
                    WHERE c2.prestamo_id = pr.id
                      AND c2.fecha_vencimiento < CURRENT_DATE
                      AND DATE_TRUNC('month', c2.fecha_vencimiento) = DATE_TRUNC('month', c.fecha_vencimiento)
                ))
        )
    )
    WHERE p.activo = TRUE
      AND p.monto_pagado IS NOT NULL
      AND p.monto_pagado > 0
      AND (pr.estado = 'APROBADO' OR p.prestamo_id IS NULL OR pr.id IS NULL)  -- Incluir pagos sin prestamo_id
      AND (c.fecha_vencimiento IS NULL OR c.fecha_vencimiento < CURRENT_DATE)  -- Si no hay cuota, usar fecha_pago
    GROUP BY COALESCE(
        DATE_TRUNC('month', c.fecha_vencimiento),
        DATE_TRUNC('month', p.fecha_pago::date)
    )
)
-- Primero: Mostrar meses con cuotas vencidas (con comparación de pagos)
SELECT 
    '=== DINERO NO COBRADO POR MES (CON CUOTAS) ===' AS tipo_calculo,
    TO_CHAR(cv.mes_vencimiento, 'YYYY-MM') AS mes,
    TO_CHAR(cv.mes_vencimiento, 'Mon YYYY') AS mes_formateado,
    COUNT(DISTINCT cv.cuota_id) AS cuotas_vencidas,
    SUM(cv.monto_programado) AS total_programado,
    COALESCE(ppm.monto_pagado_real, 0) AS total_pagado_real,
    SUM(cv.monto_programado) - COALESCE(ppm.monto_pagado_real, 0) AS dinero_no_cobrado,
    TO_CHAR(SUM(cv.monto_programado) - COALESCE(ppm.monto_pagado_real, 0), 'FM$999,999,999,990.00') AS dinero_no_cobrado_formateado,
    -- Porcentaje de cobro
    CASE 
        WHEN SUM(cv.monto_programado) > 0 THEN
            (COALESCE(ppm.monto_pagado_real, 0) / SUM(cv.monto_programado) * 100)::NUMERIC(10,2)
        ELSE 0
    END AS porcentaje_cobrado
FROM cuotas_vencidas cv
LEFT JOIN pagos_por_mes_vencimiento ppm ON cv.mes_vencimiento = ppm.mes_vencimiento
GROUP BY cv.mes_vencimiento, ppm.monto_pagado_real
ORDER BY cv.mes_vencimiento DESC;

-- Segundo: Mostrar TODOS los pagos agrupados por mes de fecha_pago (incluyendo los sin prestamo_id)
SELECT 
    '=== TOTAL PAGADO POR MES (fecha_pago) ===' AS tipo_calculo,
    TO_CHAR(DATE_TRUNC('month', p.fecha_pago::date), 'YYYY-MM') AS mes,
    TO_CHAR(DATE_TRUNC('month', p.fecha_pago::date), 'Mon YYYY') AS mes_formateado,
    COUNT(*) AS cantidad_pagos,
    SUM(p.monto_pagado) AS total_pagado,
    TO_CHAR(SUM(p.monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos p
WHERE p.activo = TRUE
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.fecha_pago IS NOT NULL
GROUP BY DATE_TRUNC('month', p.fecha_pago::date)
ORDER BY DATE_TRUNC('month', p.fecha_pago::date) DESC;

-- ============================================================================
-- 4. DINERO NO COBRADO POR PERSONA Y MES
-- ============================================================================
-- Detalle por cliente para ver quién debe más
-- ============================================================================
WITH cuotas_vencidas AS (
    SELECT 
        c.id AS cuota_id,
        c.prestamo_id,
        c.numero_cuota,
        c.fecha_vencimiento,
        DATE_TRUNC('month', c.fecha_vencimiento) AS mes_vencimiento,
        c.monto_cuota AS monto_programado,
        c.estado,
        pr.cedula
    FROM cuotas c
    INNER JOIN prestamos pr ON c.prestamo_id = pr.id
    WHERE pr.estado = 'APROBADO'
      AND c.fecha_vencimiento < CURRENT_DATE
      AND c.estado != 'PAGADO'
),
pagos_por_persona_mes AS (
    -- Sumar TODOS los monto_pagado de la tabla pagos agrupados por mes y cédula
    -- IMPORTANTE: Usa el campo monto_pagado directamente de la tabla pagos
    -- Si tiene prestamo_id, usar mes de vencimiento de cuota. Si no, usar mes de fecha_pago
    SELECT 
        COALESCE(
            DATE_TRUNC('month', c.fecha_vencimiento),
            DATE_TRUNC('month', p.fecha_pago::date)
        ) AS mes_vencimiento,
        p.cedula,
        COALESCE(SUM(p.monto_pagado), 0) AS monto_pagado_real
    FROM pagos p
    LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
    LEFT JOIN cuotas c ON (
        p.prestamo_id IS NOT NULL
        AND c.prestamo_id = p.prestamo_id 
        AND (
            (p.numero_cuota IS NOT NULL AND c.numero_cuota = p.numero_cuota)
            OR (p.numero_cuota IS NULL 
                AND c.fecha_vencimiento = (
                    SELECT MIN(c2.fecha_vencimiento)
                    FROM cuotas c2
                    WHERE c2.prestamo_id = p.prestamo_id
                      AND c2.fecha_vencimiento < CURRENT_DATE
                      AND DATE_TRUNC('month', c2.fecha_vencimiento) = DATE_TRUNC('month', c.fecha_vencimiento)
                ))
        )
    )
    WHERE p.activo = TRUE
      AND p.monto_pagado IS NOT NULL
      AND p.monto_pagado > 0
      AND (pr.estado = 'APROBADO' OR p.prestamo_id IS NULL)  -- Incluir pagos sin prestamo_id
      AND (c.fecha_vencimiento IS NULL OR c.fecha_vencimiento < CURRENT_DATE)
    GROUP BY COALESCE(
        DATE_TRUNC('month', c.fecha_vencimiento),
        DATE_TRUNC('month', p.fecha_pago::date)
    ), p.cedula
)
SELECT 
    '=== DINERO NO COBRADO POR PERSONA Y MES ===' AS tipo_calculo,
    TO_CHAR(cv.mes_vencimiento, 'YYYY-MM') AS mes,
    cv.cedula,
    COUNT(DISTINCT cv.cuota_id) AS cuotas_vencidas,
    SUM(cv.monto_programado) AS total_programado,
    COALESCE(ppm.monto_pagado_real, 0) AS total_pagado_real,
    SUM(cv.monto_programado) - COALESCE(ppm.monto_pagado_real, 0) AS dinero_no_cobrado,
    TO_CHAR(SUM(cv.monto_programado) - COALESCE(ppm.monto_pagado_real, 0), 'FM$999,999,999,990.00') AS dinero_no_cobrado_formateado
FROM cuotas_vencidas cv
LEFT JOIN pagos_por_persona_mes ppm ON (
    cv.mes_vencimiento = ppm.mes_vencimiento 
    AND cv.cedula = ppm.cedula
)
GROUP BY cv.mes_vencimiento, cv.cedula, ppm.monto_pagado_real
HAVING SUM(cv.monto_programado) - COALESCE(ppm.monto_pagado_real, 0) > 0
ORDER BY cv.mes_vencimiento DESC, dinero_no_cobrado DESC;

-- ============================================================================
-- 5. RESUMEN GENERAL PARA KPIs
-- ============================================================================
-- Métricas consolidadas para usar en dashboards
-- ============================================================================
WITH 
-- Días de mora por cliente
dias_mora_por_cliente AS (
    SELECT 
        p.cedula,
        MAX((p.fecha_pago::date - c.fecha_vencimiento)::INTEGER) AS max_dias_mora,
        AVG((p.fecha_pago::date - c.fecha_vencimiento)::INTEGER)::NUMERIC(10,2) AS avg_dias_mora
    FROM pagos p
    INNER JOIN prestamos pr ON p.prestamo_id = pr.id
    LEFT JOIN cuotas c ON (
        c.prestamo_id = p.prestamo_id 
        AND (p.numero_cuota IS NULL OR c.numero_cuota = p.numero_cuota)
    )
    WHERE p.activo = TRUE
      AND p.fecha_pago IS NOT NULL
      AND c.fecha_vencimiento IS NOT NULL
      AND p.fecha_pago::date > c.fecha_vencimiento
    GROUP BY p.cedula
),
-- Dinero no cobrado este mes
dinero_no_cobrado_mes AS (
    SELECT 
        mes_vencimiento AS mes,
        SUM(monto_programado) AS monto_programado,
        SUM(monto_pagado_real) AS monto_pagado_real,
        SUM(monto_programado) - SUM(monto_pagado_real) AS dinero_no_cobrado
    FROM (
        SELECT 
            DATE_TRUNC('month', c.fecha_vencimiento) AS mes_vencimiento,
            c.monto_cuota AS monto_programado,
            COALESCE((
                -- Sumar monto_pagado de pagos relacionados con cuotas de este mes
                SELECT SUM(p.monto_pagado)
                FROM pagos p
                LEFT JOIN prestamos pr_p ON p.prestamo_id = pr_p.id
                LEFT JOIN cuotas c_p ON (
                    p.prestamo_id IS NOT NULL
                    AND c_p.prestamo_id = p.prestamo_id 
                    AND (
                        (p.numero_cuota IS NOT NULL AND c_p.numero_cuota = p.numero_cuota)
                        OR (p.numero_cuota IS NULL 
                            AND DATE_TRUNC('month', c_p.fecha_vencimiento) = DATE_TRUNC('month', c.fecha_vencimiento)
                        )
                    )
                )
                WHERE (
                    -- Pagos relacionados con cuotas de este mes
                    DATE_TRUNC('month', c_p.fecha_vencimiento) = DATE_TRUNC('month', c.fecha_vencimiento)
                    -- O pagos sin prestamo_id pero con fecha_pago en este mes
                    OR (p.prestamo_id IS NULL 
                        AND DATE_TRUNC('month', p.fecha_pago::date) = DATE_TRUNC('month', c.fecha_vencimiento))
                )
                  AND p.activo = TRUE
                  AND p.monto_pagado IS NOT NULL
                  AND p.monto_pagado > 0
                  AND (pr_p.estado = 'APROBADO' OR p.prestamo_id IS NULL)
            ), 0) AS monto_pagado_real
        FROM cuotas c
        INNER JOIN prestamos pr ON c.prestamo_id = pr.id
        WHERE pr.estado = 'APROBADO'
          AND c.fecha_vencimiento < CURRENT_DATE
          AND c.estado != 'PAGADO'
          AND DATE_TRUNC('month', c.fecha_vencimiento) >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
    ) AS subquery
    GROUP BY mes_vencimiento
)
SELECT 
    '=== RESUMEN GENERAL PARA KPIs ===' AS tipo_calculo,
    -- Estadísticas de días de mora
    (SELECT COUNT(*) FROM dias_mora_por_cliente) AS clientes_con_mora,
    (SELECT MAX(max_dias_mora) FROM dias_mora_por_cliente) AS max_dias_mora_general,
    (SELECT AVG(avg_dias_mora) FROM dias_mora_por_cliente)::NUMERIC(10,2) AS promedio_dias_mora_general,
    -- Dinero no cobrado
    (SELECT SUM(dinero_no_cobrado) FROM dinero_no_cobrado_mes) AS total_no_cobrado_mes_actual,
    TO_CHAR((SELECT SUM(dinero_no_cobrado) FROM dinero_no_cobrado_mes), 'FM$999,999,999,990.00') AS total_no_cobrado_formateado;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

