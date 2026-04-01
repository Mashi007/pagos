-- ============================================================
-- FIX: Actualizar CHECK constraint de rol a roles RBAC
-- Ejecutar en la BD de Render (psql o DBeaver)
-- ============================================================

-- 1. Ver el constraint actual
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'usuarios'::regclass 
  AND contype = 'c';

-- 2. Eliminar constraint viejo y crear el nuevo con roles RBAC
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check;

ALTER TABLE usuarios 
ADD CONSTRAINT usuarios_rol_check 
CHECK (rol IN ('admin', 'manager', 'operator', 'viewer'));

-- 3. Corregir usuarios que puedan tener roles viejos
UPDATE usuarios SET rol = 'admin'   WHERE rol IN ('administrador', 'finiquitador');
UPDATE usuarios SET rol = 'viewer'  WHERE rol = 'operativo';

-- 4. Confirmar resultado
SELECT id, email, nombre, rol FROM usuarios ORDER BY id;
