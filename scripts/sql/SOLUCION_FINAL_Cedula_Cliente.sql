-- ============================================
-- SOLUCIÓN FINAL: CREAR Y CONFIGURAR cedula_cliente
-- ============================================
-- Este script resuelve el problema de la columna faltante
-- Ejecutar PASO por PASO y verificar cada resultado

-- ============================================
-- PASO 0: DIAGNÓSTICO INICIAL
-- ============================================
SELECT 
    '=== DIAGNÓSTICO INICIAL ===' AS seccion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula'
        ) THEN '✅ Columna "cedula" EXISTE'
        ELSE '❌ Columna "cedula" NO existe'
    END AS estado_cedula,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula_cliente'
        ) THEN '✅ Columna "cedula_cliente" EXISTE'
        ELSE '❌ Columna "cedula_cliente" NO existe - REQUIERE ACCIÓN'
    END AS estado_cedula_cliente,
    (SELECT COUNT(*) FROM pagos) AS total_registros;

-- ============================================
-- PASO 1: CREAR COLUMNA cedula_cliente (si no existe)
-- ============================================
-- ⚠️ Solo ejecutar si la columna NO existe
ALTER TABLE pagos 
ADD COLUMN IF NOT EXISTS cedula_cliente VARCHAR(20);

-- Verificar que se creó
SELECT 
    'PASO 1: Verificación post-creación' AS seccion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula_cliente'
        ) THEN '✅ Columna cedula_cliente creada exitosamente'
        ELSE '❌ ERROR: No se pudo crear la columna'
    END AS resultado;

-- ============================================
-- PASO 2: MIGRAR DATOS DE cedula A cedula_cliente
-- ============================================
-- Copiar valores desde 'cedula' a 'cedula_cliente' si existe 'cedula'
UPDATE pagos
SET cedula_cliente = cedula
WHERE cedula_cliente IS NULL
  AND cedula IS NOT NULL;

-- Verificar cuántos registros se actualizaron
SELECT 
    'PASO 2: Estadísticas de migración' AS seccion,
    COUNT(*) AS total_registros,
    COUNT(cedula) AS registros_con_cedula,
    COUNT(cedula_cliente) AS registros_con_cedula_cliente,
    COUNT(CASE WHEN cedula IS NOT NULL AND cedula_cliente IS NULL THEN 1 END) AS pendientes_migrar
FROM pagos;

-- ============================================
-- PASO 3: CREAR O VERIFICAR ÍNDICE
-- ============================================
-- El índice debería existir, pero lo creamos si no existe
CREATE INDEX IF NOT EXISTS ix_pagos_cedula_cliente 
ON pagos(cedula_cliente);

-- Verificar índices relacionados
SELECT 
    'PASO 3: Verificación de índices' AS seccion,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename = 'pagos'
    AND (indexname LIKE '%cedula%' OR indexname LIKE '%cedula_cliente%')
ORDER BY indexname;

-- ============================================
-- PASO 4: COMPARACIÓN FINAL DE DATOS
-- ============================================
SELECT 
    'PASO 4: Comparación final' AS seccion,
    COUNT(*) AS total,
    COUNT(CASE WHEN cedula = cedula_cliente THEN 1 END) AS valores_coinciden,
    COUNT(CASE WHEN cedula IS NOT NULL AND cedula_cliente IS NULL THEN 1 END) AS solo_cedula,
    COUNT(CASE WHEN cedula IS NULL AND cedula_cliente IS NOT NULL THEN 1 END) AS solo_cedula_cliente,
    COUNT(CASE WHEN cedula IS NOT NULL AND cedula_cliente IS NOT NULL AND cedula != cedula_cliente THEN 1 END) AS valores_diferentes
FROM pagos;

-- ============================================
-- PASO 5: MUESTRA DE DATOS (verificación manual)
-- ============================================
SELECT 
    'PASO 5: Muestra de datos (primeros 10 registros)' AS seccion,
    id,
    cedula,
    cedula_cliente,
    CASE 
        WHEN cedula IS NULL AND cedula_cliente IS NULL THEN 'Ambas NULL'
        WHEN cedula IS NULL THEN 'Solo cedula_cliente'
        WHEN cedula_cliente IS NULL THEN 'Solo cedula'
        WHEN cedula = cedula_cliente THEN '✅ Coinciden'
        ELSE '⚠️ Diferentes'
    END AS estado_comparacion
FROM pagos
ORDER BY id
LIMIT 10;

-- ============================================
-- PASO 6: VERIFICACIÓN DE ESTRUCTURA FINAL
-- ============================================
SELECT 
    'PASO 6: Estructura final de columnas' AS seccion,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND column_name IN ('cedula', 'cedula_cliente')
ORDER BY ordinal_position;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN FINAL ===' AS seccion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula_cliente'
        ) THEN '✅ COLUMNA cedula_cliente CREADA Y CONFIGURADA'
        ELSE '❌ ERROR: La columna no existe después de ejecutar el script'
    END AS resultado_principal,
    (SELECT COUNT(*) FROM pagos WHERE cedula_cliente IS NOT NULL) AS registros_con_cedula_cliente,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'pagos' AND indexname = 'ix_pagos_cedula_cliente'
        ) THEN '✅ Índice creado correctamente'
        ELSE '⚠️ Índice no encontrado'
    END AS estado_indice,
    'La columna cedula_cliente está lista para usar por el backend' AS siguiente_paso;

