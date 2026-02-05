-- ============================================================
-- Ver y confirmar usuarios (tabla: usuarios)
-- Ejecutar en PostgreSQL (psql, DBeaver, Render DB shell, etc.)
-- ============================================================

-- 1) Listar todos los usuarios (sin contraseña en claro; password_hash solo para confirmar que existe)
SELECT
  id,
  email,
  nombre,
  apellido,
  COALESCE(cargo, '-') AS cargo,
  rol,
  is_active,
  created_at,
  updated_at,
  last_login,
  CASE WHEN password_hash IS NOT NULL AND length(password_hash) > 0 THEN '***' ELSE NULL END AS tiene_password
FROM usuarios
ORDER BY id;

-- 2) Resumen: cuántos hay por rol y estado
SELECT
  rol,
  is_active,
  count(*) AS cantidad
FROM usuarios
GROUP BY rol, is_active
ORDER BY rol, is_active;

-- 3) Solo usuarios activos (los que pueden hacer login)
SELECT id, email, nombre, apellido, rol, created_at, last_login
FROM usuarios
WHERE is_active = true
ORDER BY id;

-- 4) Verificar que exista al menos un administrador activo (como hace GET /api/v1/usuarios/verificar-admin)
SELECT EXISTS (
  SELECT 1 FROM usuarios
  WHERE rol = 'administrador' AND is_active = true
  LIMIT 1
) AS tiene_admin_activo;

-- 5) Contar total y activos
SELECT
  count(*) AS total_usuarios,
  count(*) FILTER (WHERE is_active = true)  AS activos,
  count(*) FILTER (WHERE is_active = false) AS inactivos
FROM usuarios;
