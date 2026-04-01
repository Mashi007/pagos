-- ============================================================
-- Auditar variantes de rol "operador" y unificar a RBAC: operator
-- Ejecutar en la BD (psql o DBeaver) tras revisar el SELECT.
-- ============================================================

-- 1) Ver todos los valores distintos de rol (detectar variantes)
SELECT rol, COUNT(*) AS cantidad
FROM usuarios
GROUP BY rol
ORDER BY cantidad DESC, rol;

-- 2) Usuarios con variantes de operador (antes de unificar)
SELECT id, email, nombre, apellido, rol, is_active
FROM usuarios
WHERE LOWER(TRIM(rol)) IN ('operador', 'operario', 'operadora')
ORDER BY id;

-- 3) Unificar variantes a 'operator' (ajustar la lista si aparecen más en el paso 1)
UPDATE usuarios
SET rol = 'operator',
    updated_at = CURRENT_TIMESTAMP
WHERE LOWER(TRIM(rol)) IN ('operador', 'operario', 'operadora');

-- 4) Confirmar: solo operadores canónicos
SELECT id, email, nombre, rol
FROM usuarios
WHERE rol = 'operator'
ORDER BY id;
