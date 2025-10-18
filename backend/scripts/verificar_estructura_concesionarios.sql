-- Script para verificar la estructura real de la tabla concesionarios
-- Solo tiene una columna según el usuario

-- Verificar la estructura de la tabla concesionarios
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'concesionarios'
ORDER BY ordinal_position;

-- Verificar si hay datos en la tabla
SELECT COUNT(*) as total_registros FROM concesionarios;

-- Ver los primeros registros para entender la estructura
SELECT * FROM concesionarios LIMIT 5;
