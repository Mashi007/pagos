-- ============================================
-- VERIFICACIÓN DE COLUMNA CONCILIADO EN PAGOS_STAGING
-- ============================================
-- Este script verifica:
-- 1. Si existe la columna 'conciliado' en la tabla pagos_staging
-- 2. El estado actual de los registros (si la columna existe)
-- 3. Estadísticas de conciliación
-- ============================================

-- PASO 1: Verificar si existe la columna 'conciliado' en pagos_staging
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
  AND column_name = 'conciliado';

-- PASO 2: Si la columna existe, mostrar estadísticas
-- Descomenta las siguientes líneas si la columna existe:

-- Contar total de registros y cuántos están conciliados
/*
SELECT 
    COUNT(*) AS total_registros,
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
FROM pagos_staging;
*/

-- PASO 3: Mostrar ejemplos de registros con su estado de conciliación
-- Descomenta si la columna existe:

/*
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    conciliado,
    CASE 
        WHEN conciliado = TRUE THEN '✅ CONCILIADO'
        WHEN conciliado = FALSE THEN '❌ NO CONCILIADO'
        WHEN conciliado IS NULL THEN '⚠️ NULL'
        ELSE '❓ DESCONOCIDO'
    END AS estado_conciliacion
FROM pagos_staging
ORDER BY id_stg DESC
LIMIT 20;
*/

-- PASO 4: Verificar todas las columnas de pagos_staging para comparar
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'conciliado' THEN '✅ COLUMNA CONCILIADO EXISTE'
        ELSE ''
    END AS nota
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- PASO 5: Comparar con tabla pagos (que SÍ tiene conciliado)
SELECT 
    'pagos' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS no_conciliados,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos
UNION ALL
SELECT 
    'pagos_staging' AS tabla,
    COUNT(*) AS total_registros,
    NULL AS conciliados,  -- Si no existe la columna, será NULL
    NULL AS no_conciliados,
    NULL AS porcentaje_conciliados
FROM pagos_staging;

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. Ejecuta primero el PASO 1 para verificar si existe la columna
-- 2. Si el resultado está vacío, significa que NO existe la columna 'conciliado'
-- 3. Si el resultado muestra la columna, entonces SÍ existe
-- 4. Si existe, descomenta los PASOS 2 y 3 para ver estadísticas y ejemplos
-- 5. El PASO 4 muestra todas las columnas de pagos_staging para referencia
-- 6. El PASO 5 compara con la tabla 'pagos' que sí tiene la columna conciliado
-- ============================================

