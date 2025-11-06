-- ============================================
-- AGREGAR COLUMNA 'conciliado' A TABLA 'pagos_staging'
-- ============================================
-- Este script agrega la columna 'conciliado' y 'fecha_conciliacion' 
-- a la tabla 'pagos_staging' si no existen.
-- 
-- ⚠️ IMPORTANTE: Los datos están en pagos_staging, no en pagos.
-- ============================================

-- PASO 1: Verificar estado actual ANTES de agregar columnas
SELECT 
    'ANTES DE AGREGAR COLUMNAS' AS estado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado YA EXISTE en pagos_staging'
        ELSE '❌ Columna conciliado NO EXISTE - Se agregará'
    END AS estado_conciliado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'fecha_conciliacion'
        ) THEN '✅ Columna fecha_conciliacion YA EXISTE en pagos_staging'
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
          AND table_name = 'pagos_staging' 
          AND column_name = 'conciliado'
    ) THEN
        -- Agregar columna 'conciliado'
        ALTER TABLE pagos_staging 
        ADD COLUMN conciliado BOOLEAN NOT NULL DEFAULT FALSE;
        
        RAISE NOTICE '✅ Columna conciliado agregada exitosamente a pagos_staging';
    ELSE
        RAISE NOTICE 'ℹ️ Columna conciliado ya existe en pagos_staging - No se modifica';
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
          AND table_name = 'pagos_staging' 
          AND column_name = 'fecha_conciliacion'
    ) THEN
        -- Agregar columna 'fecha_conciliacion'
        -- Como fecha_pago es TEXT, también usamos TEXT para fecha_conciliacion por consistencia
        ALTER TABLE pagos_staging 
        ADD COLUMN fecha_conciliacion TEXT NULL;
        
        RAISE NOTICE '✅ Columna fecha_conciliacion agregada exitosamente a pagos_staging';
    ELSE
        RAISE NOTICE 'ℹ️ Columna fecha_conciliacion ya existe en pagos_staging - No se modifica';
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
              AND table_name = 'pagos_staging' 
              AND column_name = 'conciliado'
        ) THEN '✅ Columna conciliado EXISTE en pagos_staging'
        ELSE '❌ Columna conciliado NO EXISTE'
    END AS estado_conciliado,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'pagos_staging' 
              AND column_name = 'fecha_conciliacion'
        ) THEN '✅ Columna fecha_conciliacion EXISTE en pagos_staging'
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
  AND table_name = 'pagos_staging'
  AND column_name IN ('conciliado', 'fecha_conciliacion')
ORDER BY column_name;

-- ============================================
-- PASO 6: ESTADÍSTICAS INICIALES
-- ============================================
SELECT 
    'ESTADÍSTICAS INICIALES EN pagos_staging' AS estado,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS registros_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS registros_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS registros_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL THEN 1 END) AS registros_con_fecha_conciliacion
FROM pagos_staging;

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 1. Este script es idempotente: se puede ejecutar múltiples veces sin problemas
-- 2. Si las columnas ya existen, no se modificarán
-- 3. La columna 'conciliado' se crea con DEFAULT FALSE (no conciliado)
-- 4. La columna 'fecha_conciliacion' se crea como TEXT NULL (por consistencia con fecha_pago)
-- 5. Después de ejecutar este script, puedes usar Marcar_Todos_Pagos_Staging_Como_Conciliados.sql

