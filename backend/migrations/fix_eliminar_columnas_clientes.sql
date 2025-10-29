-- ==========================================
-- SCRIPT SQL PARA ELIMINAR COLUMNAS
-- modelo_vehiculo, concesionario, analista
-- DE LA TABLA clientes
-- ==========================================
-- Este script resuelve el error:
-- "null value in column 'modelo_vehiculo' of relation 'clientes' violates not-null constraint"
-- 
-- Ejecutar este script en la base de datos de producción
-- ==========================================

BEGIN;

-- Paso 1: Hacer las columnas nullable (requerido antes de eliminarlas)
ALTER TABLE clientes ALTER COLUMN modelo_vehiculo DROP NOT NULL;
ALTER TABLE clientes ALTER COLUMN concesionario DROP NOT NULL;
ALTER TABLE clientes ALTER COLUMN analista DROP NOT NULL;

-- Paso 2: Eliminar índices si existen
DROP INDEX IF EXISTS idx_clientes_modelo_vehiculo;
DROP INDEX IF EXISTS idx_clientes_concesionario;
DROP INDEX IF EXISTS idx_clientes_analista;

-- Paso 3: Eliminar las columnas
ALTER TABLE clientes DROP COLUMN IF EXISTS modelo_vehiculo;
ALTER TABLE clientes DROP COLUMN IF EXISTS concesionario;
ALTER TABLE clientes DROP COLUMN IF EXISTS analista;

COMMIT;

-- ==========================================
-- Verificación (opcional - ejecutar después)
-- ==========================================
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'clientes'
--   AND column_name IN ('modelo_vehiculo', 'concesionario', 'analista');
-- 
-- Si no devuelve filas, las columnas fueron eliminadas correctamente
-- ==========================================

