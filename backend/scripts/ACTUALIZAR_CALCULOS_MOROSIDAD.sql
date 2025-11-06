-- ============================================================================
-- SCRIPT: ACTUALIZAR CÁLCULOS DE MOROSIDAD PARA KPIs
-- ============================================================================
-- Este script actualiza los cálculos de morosidad usando:
-- 1. monto_pagado de la tabla pagos (corregido)
-- 2. monto_cuota de la tabla cuotas (programado)
-- 3. Relaciona pagos con cuotas cuando es posible
-- ============================================================================

-- ============================================================================
-- ORDEN DE EJECUCIÓN:
-- ============================================================================
-- 1. PRIMERO: Verificar datos (scripts/sql/VERIFICAR_TOTAL_PAGADO_REAL.sql)
-- 2. SEGUNDO: Calcular morosidad (scripts/sql/CALCULAR_MOROSIDAD_KPIS.sql)
-- 3. TERCERO (opcional): Actualizar tablas oficiales si existen
-- ============================================================================

-- ============================================================================
-- PASO 1: VERIFICAR QUE LOS DATOS ESTÁN CORRECTOS
-- ============================================================================
-- Ejecuta primero: scripts/sql/VERIFICAR_TOTAL_PAGADO_REAL.sql
-- Este script verifica:
-- - Total de monto_pagado en tabla pagos
-- - Pagos con prestamo_id vs sin prestamo_id
-- - Comparación entre diferentes métodos de cálculo

-- ============================================================================
-- PASO 2: CALCULAR MOROSIDAD (EJECUTAR ESTE SCRIPT)
-- ============================================================================
-- Ejecuta: scripts/sql/CALCULAR_MOROSIDAD_KPIS.sql
-- Este script calcula:
-- 1. Días de morosidad por persona
-- 2. Días de morosidad por persona y mes
-- 3. Dinero no cobrado por mes (monto_cuota vs monto_pagado)
-- 4. Dinero no cobrado por persona y mes
-- 5. Resumen general para KPIs

-- ============================================================================
-- PASO 3 (OPCIONAL): ACTUALIZAR TABLAS OFICIALES DE DASHBOARD
-- ============================================================================
-- Si existen las tablas oficiales, actualízalas:

-- 3.1. Verificar si existe la tabla dashboard_morosidad_mensual
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'dashboard_morosidad_mensual'
    ) THEN
        RAISE NOTICE '✅ Tabla dashboard_morosidad_mensual existe - Actualizando...';
        
        -- Actualizar tabla oficial de morosidad mensual
        INSERT INTO dashboard_morosidad_mensual (año, mes, morosidad_total, cantidad_cuotas_vencidas, cantidad_prestamos_afectados)
        SELECT 
            EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
            EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
            COALESCE(SUM(c.monto_cuota), 0) as morosidad_total,
            COUNT(c.id) as cantidad_cuotas_vencidas,
            COUNT(DISTINCT p.id) as cantidad_prestamos_afectados
        FROM cuotas c
        INNER JOIN prestamos p ON c.prestamo_id = p.id
        WHERE 
            p.estado = 'APROBADO'
            AND c.fecha_vencimiento < CURRENT_DATE
            AND c.estado != 'PAGADO'
        GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
        ON CONFLICT (año, mes) DO UPDATE SET
            morosidad_total = EXCLUDED.morosidad_total,
            cantidad_cuotas_vencidas = EXCLUDED.cantidad_cuotas_vencidas,
            cantidad_prestamos_afectados = EXCLUDED.cantidad_prestamos_afectados,
            fecha_actualizacion = CURRENT_TIMESTAMP;
            
        RAISE NOTICE '✅ Tabla dashboard_morosidad_mensual actualizada';
    ELSE
        RAISE NOTICE '⚠️ Tabla dashboard_morosidad_mensual NO existe - Saltando actualización';
    END IF;
END $$;

-- ============================================================================
-- RESUMEN: QUÉ HACER
-- ============================================================================
SELECT 
    '=== RESUMEN: ORDEN DE EJECUCIÓN ===' AS instruccion,
    '1. Ejecutar: VERIFICAR_TOTAL_PAGADO_REAL.sql' AS paso_1,
    '2. Ejecutar: CALCULAR_MOROSIDAD_KPIS.sql' AS paso_2,
    '3. (Opcional) Ejecutar este script para actualizar tablas oficiales' AS paso_3;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

