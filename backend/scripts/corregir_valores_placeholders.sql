-- ============================================
-- CORREGIR VALORES PLACEHOLDER
-- Los valores actuales tienen placeholders que deben ser reemplazados
-- ============================================

-- IMPORTANTE: Reemplaza estos valores con tus datos REALES antes de ejecutar

-- ============================================
-- CORREGIR VALORES
-- ============================================

-- 1. SMTP User - REEMPLAZA 'TU-EMAIL-REAL@gmail.com' con tu email real de Gmail
--    Ejemplo: 'usuario@gmail.com'
UPDATE configuracion_sistema 
SET valor = 'TU-EMAIL-REAL@gmail.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user'
AND valor = 'TU-EMAIL-REAL@gmail.com';  -- Solo actualiza si todavía tiene el placeholder

-- 2. SMTP Password - REEMPLAZA 'TU-APP-PASSWORD' con tu App Password de Gmail
--    Ejemplo: 'abcd efgh ijkl mnop' (16 caracteres, puedes quitar espacios)
--    IMPORTANTE: Debe ser App Password, NO tu contraseña normal
UPDATE configuracion_sistema 
SET valor = 'TU-APP-PASSWORD', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password'
AND valor = 'TU-APP-PASSWORD';  -- Solo actualiza si todavía tiene el placeholder

-- 3. From Email - Este parece estar bien, pero verifica que sea el correcto
--    Si necesitas cambiarlo, reemplaza 'noreply@rapicredit.com' con tu email remitente
-- UPDATE configuracion_sistema 
-- SET valor = 'noreply@rapicredit.com', actualizado_en = NOW()
-- WHERE categoria = 'EMAIL' AND clave = 'from_email';

-- ============================================
-- VERIFICAR VALORES ACTUALES (para ver qué hay que corregir)
-- ============================================
SELECT 
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN 
            CASE 
                WHEN valor LIKE 'TU-%' OR valor LIKE '<%>' THEN '❌ PLACEHOLDER: ' || valor
                ELSE '*** (oculto)'
            END
        ELSE valor
    END AS valor,
    CASE 
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        AND (valor IS NULL OR valor = '' OR valor LIKE '<%>' OR valor LIKE 'TU-%')
        THEN '❌ PENDIENTE: Reemplaza el placeholder'
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        THEN '✅ Configurado'
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

