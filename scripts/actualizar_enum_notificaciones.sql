-- ============================================================================
-- SCRIPT PARA ACTUALIZAR ENUM tiponotificacion
-- ============================================================================
-- Este script agrega los valores necesarios para notificaciones previas
-- al enum tiponotificacion si no existen
-- ============================================================================

-- 1. VERIFICAR VALORES ACTUALES DEL ENUM
-- ============================================================================
SELECT 
    t.typname AS enum_name,
    e.enumlabel AS enum_value
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'tiponotificacion'
ORDER BY e.enumsortorder;

-- FIN: Detener procesamiento aquí
-- Ejecuta las siguientes secciones solo si necesitas actualizar el enum

-- 2. AGREGAR VALORES AL ENUM (si no existen)
-- ============================================================================
-- NOTA: Ejecuta solo si los valores no existen en el enum

-- Agregar PAGO_5_DIAS_ANTES
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_5_DIAS_ANTES' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_5_DIAS_ANTES';
    END IF;
END $$;

-- Agregar PAGO_3_DIAS_ANTES
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_3_DIAS_ANTES' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_3_DIAS_ANTES';
    END IF;
END $$;

-- Agregar PAGO_1_DIA_ANTES
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_1_DIA_ANTES' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_1_DIA_ANTES';
    END IF;
END $$;

-- Agregar PAGO_DIA_0
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_DIA_0' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_DIA_0';
    END IF;
END $$;

-- Agregar PAGO_1_DIA_ATRASADO
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_1_DIA_ATRASADO' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_1_DIA_ATRASADO';
    END IF;
END $$;

-- Agregar PAGO_3_DIAS_ATRASADO
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_3_DIAS_ATRASADO' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_3_DIAS_ATRASADO';
    END IF;
END $$;

-- Agregar PAGO_5_DIAS_ATRASADO
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PAGO_5_DIAS_ATRASADO' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PAGO_5_DIAS_ATRASADO';
    END IF;
END $$;

-- Agregar PREJUDICIAL
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PREJUDICIAL' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PREJUDICIAL';
    END IF;
END $$;

-- Agregar PREJUDICIAL_1
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PREJUDICIAL_1' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PREJUDICIAL_1';
    END IF;
END $$;

-- Agregar PREJUDICIAL_2
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'PREJUDICIAL_2' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tiponotificacion')
    ) THEN
        ALTER TYPE tiponotificacion ADD VALUE 'PREJUDICIAL_2';
    END IF;
END $$;

-- 3. VERIFICAR VALORES DESPUÉS DE LA ACTUALIZACIÓN
-- ============================================================================
SELECT 
    t.typname AS enum_name,
    e.enumlabel AS enum_value
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'tiponotificacion'
ORDER BY e.enumsortorder;

-- ============================================================================
-- NOTA: Si prefieres cambiar el tipo de columna de enum a VARCHAR
-- ============================================================================
-- Descomenta las siguientes líneas si quieres convertir el enum a texto:

-- ALTER TABLE notificaciones ALTER COLUMN tipo TYPE VARCHAR(50) USING tipo::text;
-- DROP TYPE IF EXISTS tiponotificacion CASCADE;  -- Solo si ya no se usa en otros lugares

