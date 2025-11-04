-- ============================================
-- AGREGAR COLUMNA 'conciliado' A TABLA 'pagos' SI NO EXISTE
-- ============================================
-- Este script agrega la columna 'conciliado' y 'fecha_conciliacion' 
-- a la tabla 'pagos' si no existen.
-- ============================================

-- PASO 1: Verificar estado actual ANTES de agregar columnas
SELECT 
    'ANTES DE AGREGAR COLUMNAS' AS estado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado YA EXISTE'
        ELSE '❌ Columna conciliado NO EXISTE - Se agregará'
    END AS estado_conciliado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'fecha_conciliacion'
        ) THEN '✅ Columna fecha_conciliacion YA EXISTE'
        ELSE '❌ Columna fecha_conciliacion NO EXISTE - Se agregará'
    END AS estado_fecha_conciliacion;

-- ============================================
-- PASO 2: AGREGAR COLUMNA 'conciliado' SI NO EXISTE
-- ============================================
DO $$
BEGIN
    -- Verificar si la columna 'conciliado' existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'pagos' 
          AND column_name = 'conciliado'
    ) THEN
        -- Agregar columna 'conciliado'
        ALTER TABLE pagos 
        ADD COLUMN conciliado BOOLEAN NOT NULL DEFAULT FALSE;
        
        RAISE NOTICE '✅ Columna conciliado agregada exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Columna conciliado ya existe - No se modifica';
    END IF;
END $$;

-- ============================================
-- PASO 3: AGREGAR COLUMNA 'fecha_conciliacion' SI NO EXISTE
-- ============================================
DO $$
BEGIN
    -- Verificar si la columna 'fecha_conciliacion' existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'pagos' 
          AND column_name = 'fecha_conciliacion'
    ) THEN
        -- Agregar columna 'fecha_conciliacion'
        ALTER TABLE pagos 
        ADD COLUMN fecha_conciliacion TIMESTAMP NULL;
        
        RAISE NOTICE '✅ Columna fecha_conciliacion agregada exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Columna fecha_conciliacion ya existe - No se modifica';
    END IF;
END $$;

-- ============================================
-- PASO 4: VERIFICAR ESTADO DESPUÉS DE AGREGAR COLUMNAS
-- ============================================
SELECT 
    'DESPUÉS DE AGREGAR COLUMNAS' AS estado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado EXISTE'
        ELSE '❌ Columna conciliado NO EXISTE'
    END AS estado_conciliado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos' 
              AND column_name = 'fecha_conciliacion'
        ) THEN '✅ Columna fecha_conciliacion EXISTE'
        ELSE '❌ Columna fecha_conciliacion NO EXISTE'
    END AS estado_fecha_conciliacion;

-- ============================================
-- PASO 5: MOSTRAR DEFINICIÓN DE COLUMNAS AGREGADAS
-- ============================================
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos'
  AND column_name IN ('conciliado', 'fecha_conciliacion')
ORDER BY column_name;

-- ============================================
-- PASO 6: ESTADÍSTICAS INICIALES (si las columnas existen)
-- ============================================
SELECT 
    'ESTADÍSTICAS INICIALES' AS estado,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN activo = TRUE THEN 1 END) AS pagos_activos,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS pagos_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL THEN 1 END) AS pagos_con_fecha_conciliacion
FROM pagos;

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 1. Este script es idempotente: se puede ejecutar múltiples veces sin problemas
-- 2. Si las columnas ya existen, no se modificarán
-- 3. La columna 'conciliado' se crea con DEFAULT FALSE (no conciliado)
-- 4. La columna 'fecha_conciliacion' se crea como NULL (se llenará cuando se concilie)
-- 5. Después de ejecutar este script, puedes usar Marcar_Todos_Pagos_Como_Conciliados.sql

