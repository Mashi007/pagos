-- Script de verificación de migraciones de roles
-- Ejecutar después de aplicar las migraciones

-- Verificar estructura de tabla usuarios
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- Verificar datos de usuarios
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active,
    created_at
FROM usuarios 
ORDER BY id;

-- Verificar que hay al menos un admin
SELECT 
    COUNT(*) as total_usuarios,
    COUNT(CASE WHEN is_admin = TRUE THEN 1 END) as total_admins,
    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as usuarios_activos
FROM usuarios;

-- Verificar tipos de datos
SELECT 
    'is_admin' as columna,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'usuarios' AND column_name = 'is_admin';
