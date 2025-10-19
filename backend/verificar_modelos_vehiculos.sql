-- Script SQL para verificar datos de modelos de vehículos
-- Ejecutar en DBeaver

-- 1. Verificar si la tabla existe
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'modelos_vehiculos'
) as tabla_existe;

-- 2. Contar registros totales
SELECT COUNT(*) as total_registros FROM modelos_vehiculos;

-- 3. Contar registros activos
SELECT COUNT(*) as registros_activos FROM modelos_vehiculos WHERE activo = true;

-- 4. Mostrar todos los registros
SELECT id, nombre, activo, created_at, updated_at 
FROM modelos_vehiculos 
ORDER BY nombre;

-- 5. Mostrar solo registros activos (los que deberían aparecer en el dropdown)
SELECT id, nombre, activo 
FROM modelos_vehiculos 
WHERE activo = true 
ORDER BY nombre;
