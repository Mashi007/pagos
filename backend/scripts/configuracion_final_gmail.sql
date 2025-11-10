-- ============================================
-- CONFIGURACIÓN FINAL PARA GMAIL/WORKSPACE
-- Ejecutar estos comandos DESPUÉS de obtener App Password
-- ============================================

-- ============================================
-- PASO 1: OBTENER APP PASSWORD DE GMAIL
-- ============================================
-- 1. Ve a: https://myaccount.google.com/apppasswords
-- 2. Selecciona "Correo" como aplicación
-- 3. Selecciona "Otro (nombre personalizado)" como dispositivo
-- 4. Escribe "RapiCredit" como nombre
-- 5. Haz clic en "Generar"
-- 6. Copia los 16 caracteres (ej: "abcd efgh ijkl mnop")
-- 7. Úsalo en el comando de abajo (puedes quitar los espacios)
--
-- IMPORTANTE: Si no tienes 2FA activado, primero debes activarlo:
-- https://myaccount.google.com/security

-- ============================================
-- PASO 2: ACTUALIZAR CONFIGURACIÓN
-- ============================================

-- 1. SMTP User (listo - ya tiene tu email)
UPDATE configuracion_sistema 
SET valor = 'itmaster@rapicreditca.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

-- 2. SMTP Password (REEMPLAZA 'TU-APP-PASSWORD-AQUI' con tu App Password de 16 caracteres)
--    Ejemplo: Si tu App Password es "abcd efgh ijkl mnop", escribe:
--    SET valor = 'abcdefghijklmnop', actualizado_en = NOW()
--    (puedes quitar los espacios)
UPDATE configuracion_sistema 
SET valor = 'TU-APP-PASSWORD-AQUI', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

-- 3. From Email (listo - usa tu email como remitente)
UPDATE configuracion_sistema 
SET valor = 'itmaster@rapicreditca.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'from_email';

-- ============================================
-- VERIFICAR CONFIGURACIÓN
-- ============================================
SELECT 
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE 
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        AND (valor IS NULL OR valor = '' OR valor LIKE '<%>' OR valor LIKE 'TU-%')
        THEN '❌ PENDIENTE'
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        THEN '✅ Configurado'
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

