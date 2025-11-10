-- ============================================
-- ACTUALIZAR CONFIGURACIÓN EMAIL CON VALORES REALES
-- Ejecutar estos comandos en DBeaver
-- ============================================

-- ============================================
-- 1. ACTUALIZAR SMTP USER
-- ============================================
UPDATE configuracion_sistema 
SET valor = 'itmaster@rapicreditca.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

-- ============================================
-- 2. ACTUALIZAR SMTP PASSWORD
-- ============================================
-- ⚠️ IMPORTANTE: 
-- Si usas Gmail (smtp.gmail.com), NO uses tu contraseña normal.
-- Gmail requiere App Password (16 caracteres).
-- Cómo obtener: https://myaccount.google.com/apppasswords
--
-- Si NO usas Gmail, puedes usar tu contraseña normal.
-- 
-- REEMPLAZA 'TU-APP-PASSWORD-AQUI' con tu App Password de Gmail
-- O con tu contraseña normal si NO es Gmail
UPDATE configuracion_sistema 
SET valor = 'TU-APP-PASSWORD-AQUI', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

-- ============================================
-- 3. VERIFICAR FROM EMAIL
-- ============================================
-- El from_email puede ser el mismo que smtp_user o diferente
-- Si quieres usar itmaster@rapicreditca.com como remitente:
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

