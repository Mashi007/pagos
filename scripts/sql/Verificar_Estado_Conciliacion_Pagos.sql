-- ============================================
-- VERIFICACIÓN: ESTADO DE CONCILIACIÓN EN TABLAS DE PAGOS
-- ============================================
-- Este script verifica:
-- 1. Qué tablas de pagos existen (pagos, pagos_staging)
-- 2. Qué columnas tiene cada tabla
-- 3. Si existe la columna 'conciliado' en alguna de ellas
-- 4. Estado actual de conciliación
-- ============================================

-- ============================================
-- PARTE 1: VERIFICAR EXISTENCIA DE TABLAS
-- ============================================
SELECT 
    '=== VERIFICACIÓN DE TABLAS ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'pagos'
        ) THEN '✅ Tabla pagos EXISTE'
        ELSE '❌ Tabla pagos NO EXISTE'
    END AS tabla_pagos,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'pagos_staging'
        ) THEN '✅ Tabla pagos_staging EXISTE'
        ELSE '❌ Tabla pagos_staging NO EXISTE'
    END AS tabla_pagos_staging;

-- ============================================
-- PARTE 2: VERIFICAR COLUMNA 'conciliado' EN TABLA 'pagos'
-- ============================================
SELECT 
    '=== COLUMNA conciliado EN TABLA pagos ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado EXISTE en pagos'
        ELSE '❌ Columna conciliado NO EXISTE en pagos'
    END AS estado_columna;

-- Si la columna existe, mostrar su definición
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos'
  AND column_name = 'conciliado';

-- ============================================
-- PARTE 3: VERIFICAR COLUMNA 'conciliado' EN TABLA 'pagos_staging'
-- ============================================
SELECT 
    '=== COLUMNA conciliado EN TABLA pagos_staging ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado EXISTE en pagos_staging'
        ELSE '❌ Columna conciliado NO EXISTE en pagos_staging'
    END AS estado_columna;

-- Si la columna existe, mostrar su definición
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
  AND column_name = 'conciliado';

-- ============================================
-- PARTE 4: MOSTRAR TODAS LAS COLUMNAS DE 'pagos'
-- ============================================
SELECT 
    '=== TODAS LAS COLUMNAS DE TABLA pagos ===' AS verificacion,
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================
-- PARTE 5: MOSTRAR TODAS LAS COLUMNAS DE 'pagos_staging'
-- ============================================
SELECT 
    '=== TODAS LAS COLUMNAS DE TABLA pagos_staging ===' AS verificacion,
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- ============================================
-- PARTE 6: ESTADÍSTICAS DE REGISTROS (si la columna existe)
-- ============================================
-- Verificar si la columna conciliado existe en pagos antes de consultarla
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'pagos' 
          AND column_name = 'conciliado'
    ) THEN
        -- Si existe, mostrar estadísticas
        RAISE NOTICE 'Columna conciliado existe en pagos - Mostrando estadísticas';
    ELSE
        RAISE NOTICE 'Columna conciliado NO existe en pagos - No se pueden mostrar estadísticas';
    END IF;
END $$;

-- Estadísticas de pagos (solo si la columna existe)
-- Descomentar si la columna existe:
/*
SELECT 
    '=== ESTADÍSTICAS DE CONCILIACIÓN EN pagos ===' AS verificacion,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN activo = TRUE THEN 1 END) AS pagos_activos,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS pagos_con_conciliado_null
FROM pagos;
*/

-- ============================================
-- PARTE 7: RECOMENDACIÓN BASADA EN RESULTADOS
-- ============================================
SELECT 
    '=== RECOMENDACIÓN ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'conciliado'
        ) THEN 
            '✅ La columna conciliado EXISTE en pagos. Puedes usar el script Marcar_Todos_Pagos_Como_Conciliados.sql'
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'pagos'
        ) THEN 
            '⚠️ La tabla pagos EXISTE pero NO tiene columna conciliado. Necesitas crear la columna primero.'
        ELSE 
            '❌ La tabla pagos NO EXISTE. Verifica la estructura de la base de datos.'
    END AS recomendacion;

