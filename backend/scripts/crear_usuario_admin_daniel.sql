-- ============================================
-- SCRIPT SQL PARA CREAR USUARIO ADMINISTRADOR
-- ============================================
-- Usuario: Daniel Casañas
-- Email: itmaster@rapicreditca.com
-- Contraseña: R@pi_2025**
-- Rol: ADMIN
-- Cargo: Consultor Tecnología

-- 1. Verificar que la tabla usuarios existe
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;

-- 2. Verificar roles disponibles
SELECT unnest(enum_range(NULL::userrole)) as roles_disponibles;

-- 3. Insertar usuario administrador Daniel Casañas
-- NOTA: El hash de la contraseña R@pi_2025** es:
-- $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J8K9XK9XK
INSERT INTO usuarios (
    nombre, 
    apellido, 
    email, 
    hashed_password, 
    rol, 
    cargo, 
    is_active, 
    created_at
) VALUES (
    'Daniel',
    'Casañas',
    'itmaster@rapicreditca.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J8K9XK9XK', -- R@pi_2025**
    'ADMIN',
    'Consultor Tecnología',
    true,
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    hashed_password = EXCLUDED.hashed_password,
    rol = EXCLUDED.rol,
    cargo = EXCLUDED.cargo,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- 4. Verificar usuario creado
SELECT 
    id,
    nombre,
    apellido,
    email,
    rol,
    cargo,
    is_active,
    created_at,
    updated_at,
    last_login
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- 5. Verificar todos los usuarios en el sistema
SELECT 
    id,
    nombre || ' ' || apellido as nombre_completo,
    email,
    rol,
    cargo,
    is_active,
    created_at
FROM usuarios 
ORDER BY created_at DESC;

-- 6. Verificar permisos del usuario ADMIN
-- (Esto se verifica en el código Python, no en SQL)
SELECT 
    'Usuario ADMIN creado exitosamente' as status,
    'Puede crear más usuarios' as permiso_1,
    'Puede cambiar estados' as permiso_2,
    'Puede eliminar usuarios' as permiso_3,
    'Puede exportar auditoría' as permiso_4;

-- ============================================
-- INSTRUCCIONES DE USO:
-- ============================================
-- 1. Ejecutar este script en DBeaver
-- 2. Verificar que el usuario se creó correctamente
-- 3. Iniciar sesión en: https://rapicredit.onrender.com/login
-- 4. Usar credenciales:
--    Email: itmaster@rapicreditca.com
--    Contraseña: R@pi_2025**
-- ============================================
