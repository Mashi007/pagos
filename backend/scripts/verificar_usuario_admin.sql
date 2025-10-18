-- Script SQL para verificar y arreglar el usuario administrador
-- Ejecutar directamente en la base de datos

-- 1. Verificar estructura de la tabla usuarios
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 2. Verificar todos los usuarios
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active, 
    created_at, 
    last_login
FROM usuarios 
ORDER BY id;

-- 3. Verificar usuarios administradores específicamente
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active
FROM usuarios 
WHERE is_admin = TRUE;

-- 4. Verificar usuario específico itmaster@rapicreditca.com
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active, 
    created_at, 
    last_login
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- 5. Si no hay administradores, crear uno
-- Primero verificar si existe el usuario itmaster@rapicreditca.com
-- Si existe pero no es admin, marcarlo como admin:
UPDATE usuarios 
SET is_admin = TRUE 
WHERE email = 'itmaster@rapicreditca.com';

-- Si no existe ningún usuario admin, marcar el primer usuario como admin:
UPDATE usuarios 
SET is_admin = TRUE 
WHERE id = 1;

-- 6. Verificar que el usuario sea admin después del update
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- 7. Verificar que haya al menos un admin
SELECT COUNT(*) as total_admins
FROM usuarios 
WHERE is_admin = TRUE AND is_active = TRUE;
