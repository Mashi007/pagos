-- Script para verificar concesionarios en la base de datos
-- Buscar si existe "mavesa" o variaciones

-- 1. Verificar TODOS los concesionarios
SELECT 
    id,
    nombre,
    activo,
    created_at,
    updated_at
FROM concesionarios
ORDER BY id;

-- 2. Buscar específicamente "mavesa" (case insensitive)
SELECT 
    id,
    nombre,
    activo,
    created_at,
    updated_at
FROM concesionarios
WHERE LOWER(nombre) LIKE '%mavesa%'
ORDER BY id;

-- 3. Contar total de concesionarios
SELECT COUNT(*) as total_concesionarios
FROM concesionarios;

-- 4. Contar activos vs inactivos
SELECT 
    CASE 
        WHEN activo = true THEN 'Activo'
        WHEN activo = false THEN 'Inactivo'
        ELSE 'Otro'
    END as estado,
    COUNT(*) as cantidad
FROM concesionarios
GROUP BY activo
ORDER BY estado;

-- 5. Mostrar estructura de la tabla
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'concesionarios'
ORDER BY ordinal_position;

-- 6. Buscar por ID específico (ejemplo: ID 1)
SELECT 
    id,
    nombre,
    activo,
    created_at,
    updated_at
FROM concesionarios
WHERE id = 1;

-- 7. Verificar si existe created_at y updated_at
SELECT 
    CASE WHEN created_at IS NOT NULL THEN 'SI' ELSE 'NO' END as tiene_created_at,
    CASE WHEN updated_at IS NOT NULL THEN 'SI' ELSE 'NO' END as tiene_updated_at,
    COUNT(*) as cantidad_registros
FROM concesionarios;

