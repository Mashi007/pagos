-- ============================================
-- ELIMINAR COLUMNAS tasa_interes Y MORA DE prestamos_temporal
-- ============================================
-- Este script elimina las columnas tasa_interes y busca columnas relacionadas con MORA
-- ============================================

-- Verificar columnas existentes antes de eliminar
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal'
  AND (column_name LIKE '%tasa%' OR column_name LIKE '%mora%' OR column_name LIKE '%MORA%')
ORDER BY ordinal_position;

-- Eliminar columna tasa_interes si existe
ALTER TABLE prestamos_temporal 
DROP COLUMN IF EXISTS tasa_interes;

-- Buscar y eliminar columnas relacionadas con MORA (si existen)
-- Nota: No hay columna "MORA" estándar en prestamos_temporal, pero buscamos variaciones
DO $$
DECLARE
    col_name TEXT;
BEGIN
    -- Buscar columnas que contengan "mora" (case insensitive)
    FOR col_name IN 
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
          AND table_name = 'prestamos_temporal'
          AND LOWER(column_name) LIKE '%mora%'
    LOOP
        EXECUTE format('ALTER TABLE prestamos_temporal DROP COLUMN IF EXISTS %I CASCADE', col_name);
        RAISE NOTICE 'Columna eliminada: %', col_name;
    END LOOP;
END $$;

-- Verificar eliminación
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND table_name = 'prestamos_temporal'
            AND column_name = 'tasa_interes'
        ) THEN '❌ ERROR: La columna tasa_interes aún existe'
        ELSE '✅ ÉXITO: La columna tasa_interes fue eliminada correctamente'
    END as resultado_tasa_interes;

-- Mostrar columnas restantes relacionadas con interés o mora
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal'
  AND (column_name LIKE '%interes%' OR column_name LIKE '%mora%' OR column_name LIKE '%MORA%')
ORDER BY ordinal_position;

-- Mostrar total de columnas después de eliminar
SELECT 
    COUNT(*) as total_columnas_restantes
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal';
