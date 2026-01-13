-- ============================================
-- ELIMINAR COLUMNA modelo_vehiculo DE prestamos_temporal
-- ============================================
-- Este script elimina la columna modelo_vehiculo ya que se usa producto en su lugar
-- ============================================

-- Verificar si la columna existe antes de eliminarla
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND table_name = 'prestamos_temporal'
            AND column_name = 'modelo_vehiculo'
        ) THEN '✅ La columna modelo_vehiculo EXISTE'
        ELSE '❌ La columna modelo_vehiculo NO EXISTE'
    END as estado_columna;

-- Eliminar columna modelo_vehiculo si existe
ALTER TABLE prestamos_temporal 
DROP COLUMN IF EXISTS modelo_vehiculo;

-- Verificar eliminación
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND table_name = 'prestamos_temporal'
            AND column_name = 'modelo_vehiculo'
        ) THEN '❌ ERROR: La columna aún existe'
        ELSE '✅ ÉXITO: La columna fue eliminada correctamente'
    END as resultado;

-- Mostrar columnas restantes relacionadas con vehículos
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal'
  AND (column_name LIKE '%vehiculo%' OR column_name = 'producto')
ORDER BY ordinal_position;
