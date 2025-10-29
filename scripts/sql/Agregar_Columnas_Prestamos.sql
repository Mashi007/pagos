-- ============================================
-- SCRIPT DE MIGRACIÓN: AGREGAR COLUMNAS A PRÉSTAMOS
-- ============================================
-- Fecha: 2025-10-30
-- Descripción: Agrega columnas concesionario, analista y modelo_vehiculo a la tabla prestamos
-- Ejecutar en: DBeaver (Producción)
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR QUE LA TABLA prestamos EXISTE
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'prestamos'
    ) THEN
        RAISE EXCEPTION 'La tabla prestamos no existe. Ejecute primero Aplicar_Migracion_Prestamos.sql';
    END IF;
END $$;

-- ============================================
-- PASO 2: AGREGAR COLUMNAS SI NO EXISTEN
-- ============================================

-- Agregar columna concesionario
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'concesionario'
    ) THEN
        ALTER TABLE prestamos 
        ADD COLUMN concesionario VARCHAR(100);
        RAISE NOTICE '✅ Columna concesionario agregada';
    ELSE
        RAISE NOTICE '⚠️ Columna concesionario ya existe';
    END IF;
END $$;

-- Agregar columna analista
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'analista'
    ) THEN
        ALTER TABLE prestamos 
        ADD COLUMN analista VARCHAR(100);
        RAISE NOTICE '✅ Columna analista agregada';
    ELSE
        RAISE NOTICE '⚠️ Columna analista ya existe';
    END IF;
END $$;

-- Agregar columna modelo_vehiculo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'modelo_vehiculo'
    ) THEN
        ALTER TABLE prestamos 
        ADD COLUMN modelo_vehiculo VARCHAR(100);
        RAISE NOTICE '✅ Columna modelo_vehiculo agregada';
    ELSE
        RAISE NOTICE '⚠️ Columna modelo_vehiculo ya existe';
    END IF;
END $$;

-- Agregar columna usuario_autoriza
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'prestamos' AND column_name = 'usuario_autoriza'
    ) THEN
        ALTER TABLE prestamos 
        ADD COLUMN usuario_autoriza VARCHAR(100);
        RAISE NOTICE '✅ Columna usuario_autoriza agregada';
    ELSE
        RAISE NOTICE '⚠️ Columna usuario_autoriza ya existe';
    END IF;
END $$;

-- ============================================
-- PASO 3: VERIFICAR ESTRUCTURA DE LA TABLA
-- ============================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos'
    AND column_name IN ('concesionario', 'analista', 'modelo_vehiculo', 'usuario_autoriza')
ORDER BY ordinal_position;

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

