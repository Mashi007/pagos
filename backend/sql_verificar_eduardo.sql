-- Verificar rol de Eduardo Cappecci

SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    is_active
FROM usuarios 
WHERE email = 'operaciones@rapicreditca.com';

-- Si necesitas cambiar el rol a admin:
-- UPDATE usuarios SET rol = 'admin' WHERE email = 'operaciones@rapicreditca.com';
