-- Actualizar roles de usuarios que deben ser 'operator'
UPDATE usuarios SET rol = 'operator' 
WHERE email IN (
    'cobranza@rapicreditca.com',
    'bgonzalez.rapicredit@gmail.com',
    'sestrella.rapicredit@gmail.com',
    'lescalona.rapicredit@gmail.com'
);

-- Verificar resultado
SELECT id, email, nombre, apellido, rol FROM usuarios ORDER BY id;
