-- ============================================================================
-- GENERACIÓN MASIVA DE CUOTAS EN SQL PURO
-- Script para ejecutar en DBeaver - Evita problemas de encoding de Python
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar préstamos que necesitan cuotas
-- ============================================================================
SELECT 
    'Préstamos aprobados sin cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO' 
    AND c.id IS NULL;

-- ============================================================================
-- PASO 2: Eliminar cuotas existentes de préstamos que se regenerarán
-- ============================================================================
-- ⚠️ SOLO EJECUTAR SI QUIERES REGENERAR CUOTAS EXISTENTES
-- Comentar si solo quieres agregar cuotas faltantes

/*
DELETE FROM cuotas
WHERE prestamo_id IN (
    SELECT p.id
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
        AND (
            c.id IS NULL  -- Sin cuotas
            OR (
                SELECT COUNT(*) FROM cuotas c2 
                WHERE c2.prestamo_id = p.id
            ) != p.numero_cuotas  -- Cuotas incompletas
        )
);
*/

-- ============================================================================
-- PASO 3: GENERAR CUOTAS (Script principal)
-- ============================================================================
-- Este INSERT genera todas las cuotas necesarias
-- Usa método Francés simplificado (cuota fija)

-- IMPORTANTE: Este script genera cuotas para todos los préstamos aprobados sin cuotas
-- Puede tardar varios minutos si hay miles de préstamos

WITH prestamos_sin_cuotas AS (
    -- Identificar préstamos que necesitan cuotas
    SELECT 
        p.id,
        p.total_financiamiento,
        p.numero_cuotas,
        p.cuota_periodo,
        p.tasa_interes,
        p.modalidad_pago,
        p.fecha_base_calculo
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
        AND p.fecha_base_calculo IS NOT NULL
        AND p.total_financiamiento > 0
        AND p.numero_cuotas > 0
        AND c.id IS NULL  -- Sin cuotas
    GROUP BY p.id, p.total_financiamiento, p.numero_cuotas, p.cuota_periodo,
             p.tasa_interes, p.modalidad_pago, p.fecha_base_calculo
)
INSERT INTO cuotas (
    prestamo_id,
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    monto_capital,
    monto_interes,
    saldo_capital_inicial,
    saldo_capital_final,
    capital_pagado,
    interes_pagado,
    mora_pagada,
    total_pagado,
    capital_pendiente,
    interes_pendiente,
    monto_mora,
    tasa_mora,
    dias_mora,
    estado,
    fecha_pago
)
SELECT 
    p.id AS prestamo_id,
    serie AS numero_cuota,
    -- Fecha de vencimiento: fecha_base_calculo + (numero_cuota * intervalo_dias)
    (
        p.fecha_base_calculo + 
        (
            serie * 
            CASE 
                WHEN p.modalidad_pago = 'MENSUAL' THEN 30
                WHEN p.modalidad_pago = 'QUINCENAL' THEN 15
                WHEN p.modalidad_pago = 'SEMANAL' THEN 7
                ELSE 30
            END
        ) || ' days'
    )::INTERVAL::DATE AS fecha_vencimiento,
    p.cuota_periodo AS monto_cuota,
    -- Calcular capital e interés (método simplificado)
    CASE 
        WHEN p.tasa_interes = 0 THEN p.cuota_periodo
        ELSE GREATEST(0, p.cuota_periodo - (p.cuota_periodo * (p.tasa_interes / 100.0 / 12.0)))
    END AS monto_capital,
    CASE 
        WHEN p.tasa_interes = 0 THEN 0
        ELSE p.cuota_periodo * (p.tasa_interes / 100.0 / 12.0)
    END AS monto_interes,
    -- Saldos inicial y final (aproximados - para método Francés exacto se necesitaría iteración)
    GREATEST(0, p.total_financiamiento - (serie * p.cuota_periodo)) AS saldo_capital_inicial,
    GREATEST(0, p.total_financiamiento - ((serie - 1) * p.cuota_periodo)) AS saldo_capital_final,
    -- Valores iniciales (todo pendiente)
    0 AS capital_pagado,
    0 AS interes_pagado,
    0 AS mora_pagada,
    0 AS total_pagado,
    CASE 
        WHEN p.tasa_interes = 0 THEN p.cuota_periodo
        ELSE GREATEST(0, p.cuota_periodo - (p.cuota_periodo * (p.tasa_interes / 100.0 / 12.0)))
    END AS capital_pendiente,
    CASE 
        WHEN p.tasa_interes = 0 THEN 0
        ELSE p.cuota_periodo * (p.tasa_interes / 100.0 / 12.0)
    END AS interes_pendiente,
    0 AS monto_mora,
    0 AS tasa_mora,
    0 AS dias_mora,
    'PENDIENTE' AS estado,
    NULL AS fecha_pago
FROM prestamos_sin_cuotas p,
     LATERAL GENERATE_SERIES(1, p.numero_cuotas) AS serie
WHERE NOT EXISTS (
    SELECT 1 FROM cuotas c 
    WHERE c.prestamo_id = p.id 
    AND c.numero_cuota = serie
);

-- ============================================================================
-- PASO 4: Verificar cuotas generadas
-- ============================================================================

-- Total de cuotas generadas
SELECT 
    'Total cuotas generadas' AS metrica,
    COUNT(*) AS cantidad
FROM cuotas;

-- Préstamos aprobados sin cuotas (debe ser 0 o muy bajo)
SELECT 
    'Préstamos aprobados SIN cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO' 
    AND c.id IS NULL;

-- Comparar número planificado vs real
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_reales,
    CASE 
        WHEN p.numero_cuotas = COUNT(c.id) THEN 'OK'
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        ELSE 'INCONSISTENTE'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING p.numero_cuotas != COUNT(c.id) OR COUNT(c.id) = 0
ORDER BY p.id
LIMIT 20;

-- Ejemplo de cuotas generadas (primeros 10 préstamos)
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    p.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.estado
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;
