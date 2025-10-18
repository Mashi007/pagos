-- ============================================
-- CONSULTA PARA VERIFICAR ROL DEL USUARIO DANIEL
-- ============================================

-- 1. Consultar información del usuario Daniel
SELECT 
    id,
    nombre || ' ' || apellido as nombre_completo,
    email,
    rol,
    cargo,
    is_active,
    created_at,
    last_login
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- 2. Mostrar todos los usuarios en el sistema
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

-- 3. Verificar roles disponibles en el sistema
SELECT unnest(enum_range(NULL::userrole)) as roles_disponibles;
