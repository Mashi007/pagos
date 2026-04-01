-- Verificar si operaciones@rapicreditca.com es admin

SELECT 
    id,
    email,
    nombre,
    apellido,
    cargo,
    rol,
    is_active,
    created_at,
    last_login
FROM usuarios 
WHERE email = 'operaciones@rapicreditca.com'
OR email = 'itmaster@rapicreditca.com'
ORDER BY email;
