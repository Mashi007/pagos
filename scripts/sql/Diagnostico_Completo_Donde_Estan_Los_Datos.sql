-- ============================================
-- DIAGNÓSTICO: ¿DÓNDE ESTÁN LOS DATOS DE PAGOS?
-- ============================================
-- Este script verifica en qué tabla están realmente los datos de pagos
-- ============================================

-- PASO 1: Verificar cantidad de registros en cada tabla
SELECT 
    '=== CANTIDAD DE REGISTROS POR TABLA ===' AS verificacion,
    'pagos' AS tabla,
    COUNT(*) AS total_registros
FROM pagos
UNION ALL
SELECT 
    '=== CANTIDAD DE REGISTROS POR TABLA ===' AS verificacion,
    'pagos_staging' AS tabla,
    COUNT(*) AS total_registros
FROM pagos_staging;

-- PASO 2: Comparar registros entre tablas
SELECT 
    '=== COMPARACIÓN DE REGISTROS ===' AS verificacion,
    (SELECT COUNT(*) FROM pagos) AS total_pagos,
    (SELECT COUNT(*) FROM pagos_staging) AS total_pagos_staging,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos_staging) = 0 AND (SELECT COUNT(*) FROM pagos) > 0 THEN 
            '✅ Los datos están en TABLA pagos (no en pagos_staging)'
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 AND (SELECT COUNT(*) FROM pagos) = 0 THEN 
            '✅ Los datos están en TABLA pagos_staging (no en pagos)'
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 AND (SELECT COUNT(*) FROM pagos) > 0 THEN 
            '⚠️ Hay datos en AMBAS tablas'
        ELSE 
            '❌ AMBAS tablas están VACÍAS'
    END AS conclusion;

-- PASO 3: Verificar si pagos tiene columna conciliado y cuántos están conciliados
SELECT 
    '=== ESTADO DE CONCILIACIÓN EN TABLA pagos ===' AS verificacion,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN activo = TRUE THEN 1 END) AS pagos_activos,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS pagos_con_conciliado_null,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos;

-- PASO 4: Verificar si pagos_staging tiene columna conciliado y cuántos están conciliados
SELECT 
    '=== ESTADO DE CONCILIACIÓN EN TABLA pagos_staging ===' AS verificacion,
    COUNT(*) AS total_registros,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) THEN COUNT(CASE WHEN conciliado = TRUE THEN 1 END)
        ELSE NULL
    END AS registros_conciliados,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) THEN COUNT(CASE WHEN conciliado = FALSE THEN 1 END)
        ELSE NULL
    END AS registros_no_conciliados,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) AND COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE NULL
    END AS porcentaje_conciliados
FROM pagos_staging;

-- PASO 5: Recomendación final
SELECT 
    '=== RECOMENDACIÓN ===' AS verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos_staging) = 0 AND (SELECT COUNT(*) FROM pagos) > 0 THEN 
            '✅ Usar script: Marcar_Todos_Pagos_Como_Conciliados.sql (los datos están en pagos)'
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 AND (SELECT COUNT(*) FROM pagos) = 0 THEN 
            '✅ Usar script: Marcar_Todos_Pagos_Staging_Como_Conciliados.sql (los datos están en pagos_staging)'
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 AND (SELECT COUNT(*) FROM pagos) > 0 THEN 
            '⚠️ Ejecutar AMBOS scripts: Marcar_Todos_Pagos_Como_Conciliados.sql Y Marcar_Todos_Pagos_Staging_Como_Conciliados.sql'
        ELSE 
            '❌ NO HAY DATOS en ninguna tabla. Necesitas cargar datos primero.'
    END AS recomendacion;

