-- ============================================================================
-- APLICAR PAGOS PENDIENTES A CUOTAS - SQL PARA DBEAVER
-- Este script aplica los pagos a las cuotas de forma secuencial
-- ============================================================================

-- PASO 1: Identificar pagos pendientes de aplicar
SELECT 
    'PASO 1: Pagos pendientes de aplicar' AS seccion;

WITH pagos_pendientes AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado,
        p.fecha_pago,
        COUNT(DISTINCT c.id) AS total_cuotas,
        COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_actual
    FROM pagos p
    LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
    WHERE p.prestamo_id IS NOT NULL
        AND p.monto_pagado > 0
    GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.fecha_pago
    HAVING COALESCE(SUM(c.total_pagado), 0) < p.monto_pagado
        OR COUNT(DISTINCT c.id) = 0
)
SELECT 
    COUNT(*) AS total_pagos_pendientes,
    COUNT(DISTINCT prestamo_id) AS prestamos_afectados,
    COALESCE(SUM(monto_pagado), 0) AS monto_total_pendiente
FROM pagos_pendientes;

-- PASO 2: PREVIEW - Ver cómo se aplicarían los pagos
SELECT 
    'PASO 2: Preview de aplicacion de pagos' AS seccion;

WITH pagos_pendientes_ordenados AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado,
        p.fecha_pago,
        ROW_NUMBER() OVER (PARTITION BY p.prestamo_id ORDER BY p.fecha_pago ASC, p.id ASC) AS orden_pago
    FROM pagos p
    WHERE p.prestamo_id IS NOT NULL
        AND p.monto_pagado > 0
        AND NOT EXISTS (
            SELECT 1 
            FROM cuotas c 
            WHERE c.prestamo_id = p.prestamo_id 
                AND c.total_pagado > 0
                AND c.fecha_pago >= p.fecha_pago
        )
),
cuotas_pendientes_ordenadas AS (
    SELECT 
        c.id AS cuota_id,
        c.prestamo_id,
        c.numero_cuota,
        c.monto_cuota,
        c.monto_capital,
        c.monto_interes,
        c.total_pagado,
        c.capital_pagado,
        c.interes_pagado,
        c.capital_pendiente,
        c.interes_pendiente,
        c.fecha_vencimiento,
        ROW_NUMBER() OVER (PARTITION BY c.prestamo_id ORDER BY c.numero_cuota ASC) AS orden_cuota
    FROM cuotas c
    WHERE c.estado != 'PAGADO'
)
SELECT 
    ppo.pago_id,
    ppo.prestamo_id,
    ppo.monto_pagado AS monto_pago,
    TO_CHAR(ppo.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    cpo.cuota_id,
    cpo.numero_cuota,
    cpo.monto_cuota,
    cpo.total_pagado AS total_pagado_actual,
    cpo.monto_cuota - cpo.total_pagado AS monto_faltante,
    LEAST(ppo.monto_pagado, cpo.monto_cuota - cpo.total_pagado) AS monto_a_aplicar,
    CASE 
        WHEN cpo.monto_cuota - cpo.total_pagado <= 0 THEN 'Ya pagada'
        WHEN ppo.monto_pagado >= (cpo.monto_cuota - cpo.total_pagado) THEN 'Completara cuota'
        ELSE 'Parcial'
    END AS tipo_aplicacion
FROM pagos_pendientes_ordenados ppo
INNER JOIN cuotas_pendientes_ordenadas cpo ON ppo.prestamo_id = cpo.prestamo_id
    AND ppo.orden_pago = cpo.orden_cuota  -- Aplicar pago N a cuota N
WHERE cpo.monto_cuota - cpo.total_pagado > 0
ORDER BY ppo.prestamo_id, ppo.fecha_pago ASC
LIMIT 100;

-- ============================================================================
-- PASO 3: APLICAR PAGOS A CUOTAS (VERSION SIMPLIFICADA)
-- IMPORTANTE: Esta es una versión simplificada. Para lógica completa, usar backend
-- ============================================================================

-- Esta función aplica el pago proporcionalmente entre capital e interés
-- y actualiza el estado de la cuota

-- Primero, crear una función auxiliar si no existe (PostgreSQL)
-- Ejecutar esta función primero de forma separada si hay problemas con DO $$
CREATE OR REPLACE FUNCTION aplicar_pago_a_cuota_sql(
    p_cuota_id INTEGER,
    p_monto_aplicar NUMERIC
) RETURNS BOOLEAN AS $func$
DECLARE
    v_cuota RECORD;
    v_proporcion_capital NUMERIC;
    v_proporcion_interes NUMERIC;
    v_capital_aplicar NUMERIC;
    v_interes_aplicar NUMERIC;
    v_total_pagado_nuevo NUMERIC;
BEGIN
    -- Obtener datos de la cuota
    SELECT 
        monto_cuota,
        monto_capital,
        monto_interes,
        total_pagado,
        capital_pagado,
        interes_pagado,
        capital_pendiente,
        interes_pendiente,
        fecha_vencimiento,
        estado
    INTO v_cuota
    FROM cuotas
    WHERE id = p_cuota_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Calcular proporción
    IF (v_cuota.capital_pendiente + v_cuota.interes_pendiente) > 0 THEN
        v_proporcion_capital := v_cuota.capital_pendiente / (v_cuota.capital_pendiente + v_cuota.interes_pendiente);
        v_proporcion_interes := v_cuota.interes_pendiente / (v_cuota.capital_pendiente + v_cuota.interes_pendiente);
    ELSE
        v_proporcion_capital := 1;
        v_proporcion_interes := 0;
    END IF;
    
    -- Calcular montos a aplicar
    v_capital_aplicar := p_monto_aplicar * v_proporcion_capital;
    v_interes_aplicar := p_monto_aplicar * v_proporcion_interes;
    
    -- Actualizar cuota
    UPDATE cuotas
    SET 
        capital_pagado = capital_pagado + v_capital_aplicar,
        interes_pagado = interes_pagado + v_interes_aplicar,
        total_pagado = total_pagado + p_monto_aplicar,
        capital_pendiente = GREATEST(0, capital_pendiente - v_capital_aplicar),
        interes_pendiente = GREATEST(0, interes_pendiente - v_interes_aplicar),
        fecha_pago = CURRENT_DATE,
        estado = CASE 
            WHEN (total_pagado + p_monto_aplicar) >= monto_cuota THEN 'PAGADO'
            WHEN fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO'
            ELSE 'PENDIENTE'
        END
    WHERE id = p_cuota_id;
    
    RETURN TRUE;
END;
$func$ LANGUAGE plpgsql;

-- PASO 4: Aplicar pagos secuencialmente (proceso por proceso)
-- NOTA: Este es un ejemplo simplificado. Para aplicar todos los pagos,
-- ejecutar este bloque múltiples veces o crear un loop

-- Ejemplo: Aplicar primer pago pendiente de cada préstamo
WITH pagos_pendientes_ordenados AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado AS saldo_restante,
        p.fecha_pago,
        ROW_NUMBER() OVER (PARTITION BY p.prestamo_id ORDER BY p.fecha_pago ASC, p.id ASC) AS rn
    FROM pagos p
    WHERE p.prestamo_id IS NOT NULL
        AND p.monto_pagado > 0
        AND NOT EXISTS (
            SELECT 1 
            FROM cuotas c 
            WHERE c.prestamo_id = p.prestamo_id 
                AND c.total_pagado > 0
                AND c.fecha_pago >= p.fecha_pago
        )
),
cuotas_pendientes AS (
    SELECT 
        c.id AS cuota_id,
        c.prestamo_id,
        c.numero_cuota,
        c.monto_cuota - c.total_pagado AS monto_faltante,
        ROW_NUMBER() OVER (PARTITION BY c.prestamo_id ORDER BY c.numero_cuota ASC) AS rn
    FROM cuotas c
    WHERE c.estado != 'PAGADO'
        AND (c.monto_cuota - c.total_pagado) > 0
),
asignacion_pagos_cuotas AS (
    SELECT 
        ppo.pago_id,
        cpo.cuota_id,
        ppo.saldo_restante,
        cpo.monto_faltante,
        LEAST(ppo.saldo_restante, cpo.monto_faltante) AS monto_aplicar
    FROM pagos_pendientes_ordenados ppo
    INNER JOIN cuotas_pendientes cpo ON ppo.prestamo_id = cpo.prestamo_id 
        AND ppo.rn = cpo.rn
)
SELECT 
    'PASO 4: Aplicacion de pagos (PREVIEW)' AS seccion,
    pago_id,
    cuota_id,
    monto_aplicar,
    CASE 
        WHEN monto_aplicar >= monto_faltante THEN 'Completara cuota'
        ELSE 'Parcial'
    END AS tipo
FROM asignacion_pagos_cuotas
ORDER BY pago_id
LIMIT 50;

-- ============================================================================
-- PASO 5: EJECUTAR APLICACION (COMENTADO POR SEGURIDAD)
-- Descomentar para ejecutar. Ejecutar en lotes pequeños primero.
-- ============================================================================

/*
-- Aplicar pagos a cuotas (versión simplificada)
DO $$
DECLARE
    v_pago RECORD;
    v_cuota RECORD;
    v_saldo_restante NUMERIC;
    v_monto_aplicar NUMERIC;
    v_aplicado BOOLEAN;
BEGIN
    -- Iterar sobre pagos pendientes
    FOR v_pago IN 
        SELECT 
            p.id AS pago_id,
            p.prestamo_id,
            p.monto_pagado,
            p.fecha_pago
        FROM pagos p
        WHERE p.prestamo_id IS NOT NULL
            AND p.monto_pagado > 0
        ORDER BY p.prestamo_id, p.fecha_pago ASC, p.id ASC
        LIMIT 100  -- Procesar en lotes de 100
    LOOP
        v_saldo_restante := v_pago.monto_pagado;
        
        -- Aplicar a cuotas pendientes del préstamo
        FOR v_cuota IN 
            SELECT 
                c.id AS cuota_id,
                c.monto_cuota - c.total_pagado AS monto_faltante
            FROM cuotas c
            WHERE c.prestamo_id = v_pago.prestamo_id
                AND c.estado != 'PAGADO'
                AND (c.monto_cuota - c.total_pagado) > 0
            ORDER BY c.numero_cuota ASC
        LOOP
            IF v_saldo_restante <= 0 THEN
                EXIT;
            END IF;
            
            v_monto_aplicar := LEAST(v_saldo_restante, v_cuota.monto_faltante);
            v_aplicado := aplicar_pago_a_cuota_sql(v_cuota.cuota_id, v_monto_aplicar);
            
            IF v_aplicado THEN
                v_saldo_restante := v_saldo_restante - v_monto_aplicar;
            END IF;
        END LOOP;
        
        RAISE NOTICE 'Pago % procesado. Saldo restante: %', v_pago.pago_id, v_saldo_restante;
    END LOOP;
    
    COMMIT;
END $$;
*/

-- PASO 6: Verificar resultados después de aplicar
SELECT 
    'PASO 6: Verificacion de aplicacion' AS seccion;

SELECT 
    COUNT(DISTINCT p.id) AS total_pagos_con_prestamo,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN p.id END) AS pagos_aplicados,
    COUNT(DISTINCT CASE WHEN c.total_pagado = 0 AND p.monto_pagado > 0 THEN p.id END) AS pagos_sin_aplicar,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL;

