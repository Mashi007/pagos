-- Verificar estado del usuario operaciones@rapicreditca.com
-- Ejecutar en DBeaver o cliente SQL

SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    is_admin,
    is_active,
    cargo,
    created_at,
    updated_at,
    last_login,
    CASE 
        WHEN is_active = true THEN '✅ ACTIVO'
        ELSE '❌ INACTIVO'
    END as estado_activo,
    CASE 
        WHEN is_admin = true THEN '👑 ADMINISTRADOR'
        ELSE '👤 USUARIO'
    END as tipo_usuario
FROM users
WHERE email = 'operaciones@rapicreditca.com';

-- Si no existe, mostrar todos los usuarios para referencia
-- SELECT email, nombre, apellido, is_active, is_admin FROM users ORDER BY email;

