-- Ejemplos de SQL para crear usuarios con rol finiquitador
-- Aplicar DESPUÉS de ejecutar: alembic upgrade head

-- OPCIÓN 1: Usuario finiquitador simple
INSERT INTO usuarios (email, password_hash, nombre, apellido, cargo, rol, is_active)
VALUES (
  'finiquitador@rapicredit.com',
  -- Generar este hash con: python -c "from app.core.security import hash_password; print(hash_password('tu_password'))"
  '$2b$12$ejemplo_hash_bcrypt_aqui',
  'María',
  'Gestora de Finiquitos',
  'Gestor de Finiquitos',
  'finiquitador',
  true
)
ON CONFLICT (email) DO NOTHING;

-- OPCIÓN 2: Usuario finiquitador por equipo
INSERT INTO usuarios (email, password_hash, nombre, apellido, cargo, rol, is_active)
VALUES 
  ('finiquitador.equipo1@rapicredit.com', '$2b$12$ejemplo_hash_1', 'Juan', 'Pérez', 'Finiquitador', 'finiquitador', true),
  ('finiquitador.equipo2@rapicredit.com', '$2b$12$ejemplo_hash_2', 'Carmen', 'López', 'Finiquitadora', 'finiquitador', true),
  ('finiquitador.equipo3@rapicredit.com', '$2b$12$ejemplo_hash_3', 'Roberto', 'Martínez', 'Finiquitador', 'finiquitador', true)
ON CONFLICT (email) DO NOTHING;

-- OPCIÓN 3: Convertir usuario existente a finiquitador
UPDATE usuarios 
SET rol = 'finiquitador'
WHERE email = 'usuario_existente@rapicredit.com';

-- OPCIÓN 4: Ver todos los usuarios por rol
SELECT 
  id,
  email,
  nombre,
  apellido,
  cargo,
  rol,
  is_active,
  created_at
FROM usuarios
ORDER BY rol, nombre
LIMIT 100;

-- OPCIÓN 5: Ver solo finiquitadores
SELECT 
  id,
  email,
  nombre,
  apellido,
  cargo,
  is_active,
  created_at,
  last_login
FROM usuarios
WHERE rol = 'finiquitador'
ORDER BY created_at DESC;

-- OPCIÓN 6: Desactivar un finiquitador (sin borrar)
UPDATE usuarios
SET is_active = false
WHERE email = 'finiquitador@rapicredit.com';

-- OPCIÓN 7: Cambiar finiquitador a operativo
UPDATE usuarios
SET rol = 'operativo'
WHERE email = 'finiquitador@rapicredit.com';

-- OPCIÓN 8: Ver estadísticas por rol
SELECT 
  rol,
  COUNT(*) as cantidad,
  SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as activos,
  SUM(CASE WHEN is_active = false THEN 1 ELSE 0 END) as inactivos
FROM usuarios
GROUP BY rol
ORDER BY rol;

-- OPCIÓN 9: Auditoría: ver cambios de rol (si tienes auditoría)
-- Ejecutar si tienes tabla de auditoría
-- SELECT * FROM auditorias WHERE tabla = 'usuarios' AND columna = 'rol' ORDER BY fecha DESC LIMIT 20;

-- OPCIÓN 10: Script seguro para cambios en lote
-- Cambiar múltiples usuarios a finiquitador de forma segura
BEGIN;
  UPDATE usuarios
  SET rol = 'finiquitador'
  WHERE email IN (
    'user1@rapicredit.com',
    'user2@rapicredit.com',
    'user3@rapicredit.com'
  );
  
  -- Verificar cambios antes de hacer COMMIT
  SELECT email, rol FROM usuarios 
  WHERE email IN ('user1@rapicredit.com', 'user2@rapicredit.com', 'user3@rapicredit.com');
  
  -- Si todo se ve bien, descomenta:
  -- COMMIT;
  -- Si algo está mal:
  -- ROLLBACK;
END;

-- Verificación post-aplicación
-- Ejecutar esto para confirmar que la migración se aplicó correctamente:
-- 1. Verifica que existe el constraint
SELECT constraint_name 
FROM information_schema.table_constraints 
WHERE table_name='usuarios' AND constraint_type='CHECK';

-- 2. Intenta insertar un rol inválido (debería fallar)
-- INSERT INTO usuarios (email, password_hash, nombre, apellido, rol) 
-- VALUES ('test@test.com', 'hash', 'Test', 'User', 'rol_invalido');

-- 3. Intenta insertar un rol válido (debería funcionar)
-- INSERT INTO usuarios (email, password_hash, nombre, apellido, rol, is_active) 
-- VALUES ('test.finiquitador@test.com', 'hash', 'Test', 'Finiquitador', 'finiquitador', true);
