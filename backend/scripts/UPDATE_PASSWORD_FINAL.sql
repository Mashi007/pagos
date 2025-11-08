-- ============================================================================
-- SCRIPT SQL PARA ACTUALIZAR CONTRASEÑA EN BASE DE DATOS
-- ============================================================================
-- 
-- Usuario: itmaster@rapicreditca.com
-- Nueva contraseña: Casa1803+
-- Hash generado: $2b$12$jk/udpXaYwEaPi3WINUZ3eKVb3Rio8CUEOksiT4Pq0OXRE3Ka0KOm
--
-- INSTRUCCIONES:
-- 1. Ejecuta este script en tu base de datos PostgreSQL
-- 2. Verifica que el usuario existe antes de actualizar
-- 3. Los cambios se confirman automáticamente con COMMIT
--
-- Para ejecutar desde línea de comandos:
--   psql -U tu_usuario -d tu_base_de_datos -f UPDATE_PASSWORD_FINAL.sql
--
-- O copia y pega este contenido en pgAdmin, DBeaver, o tu cliente SQL favorito
-- ============================================================================

BEGIN;

-- Paso 1: Verificar que el usuario existe
SELECT 
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    created_at,
    updated_at
FROM users
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 2: Actualizar contraseña con hash generado
UPDATE users
SET 
    hashed_password = '$2b$12$jk/udpXaYwEaPi3WINUZ3eKVb3Rio8CUEOksiT4Pq0OXRE3Ka0KOm',
    updated_at = NOW()
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 3: Verificar que se actualizó correctamente
SELECT 
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at,
    CASE 
        WHEN updated_at > NOW() - INTERVAL '1 minute' THEN 'Contrasena actualizada correctamente'
        ELSE 'Verificar actualizacion'
    END as estado
FROM users
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 4: Confirmar cambios
COMMIT;

-- ============================================================================
-- Script completado
-- Ahora puedes iniciar sesion con:
--   Email: itmaster@rapicreditca.com
--   Contrasena: Casa1803+
-- ============================================================================

