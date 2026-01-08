-- =====================================================
-- LIMPIAR TABLA Y PREPARAR PARA IMPORTACIÓN
-- Ejecutar ANTES de importar CSV
-- =====================================================

-- Eliminar el registro de prueba
DELETE FROM clientes_temp;

-- Verificar que está vacía
SELECT 
    'Registros en clientes_temp (debe ser 0)' as verificacion,
    COUNT(*) as cantidad
FROM clientes_temp;

-- Verificar estructura de la tabla
SELECT 
    'Tabla lista para importar' as estado,
    COUNT(*) as columnas
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'clientes_temp';

