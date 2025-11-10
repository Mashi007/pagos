-- ============================================
-- SCRIPT PARA ACTUALIZAR VALORES PENDIENTES
-- Reemplaza los valores que tienen < >
-- ============================================

-- IMPORTANTE: Reemplaza los valores entre < > con tus datos reales antes de ejecutar

-- ============================================
-- ACTUALIZAR VALORES PENDIENTES
-- ============================================
-- 
-- INSTRUCCIONES:
-- 1. Reemplaza TODO el texto entre las comillas (incluyendo los < >)
-- 2. Ejemplo: '<TU-EMAIL@gmail.com>' → 'miemail@gmail.com' (sin los < >)
-- 3. NO dejes los < > en los valores finales
--
-- ============================================

-- 1. SMTP User (REEMPLAZA '<TU-EMAIL@gmail.com>' con tu email real)
--    Ejemplo: 'miemail@gmail.com' (sin los < >)
UPDATE configuracion_sistema 
SET valor = '<TU-EMAIL@gmail.com>', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

-- 2. SMTP Password (REEMPLAZA '<TU-APP-PASSWORD>' con tu App Password de Gmail)
--    Ejemplo: 'abcd efgh ijkl mnop' (16 caracteres, puedes quitar los espacios)
--    IMPORTANTE: Gmail requiere App Password, NO tu contraseña normal
UPDATE configuracion_sistema 
SET valor = '<TU-APP-PASSWORD>', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

-- 3. From Email (REEMPLAZA '<noreply@rapicredit.com>' con tu email remitente)
--    Ejemplo: 'noreply@rapicredit.com' o 'tu-email@gmail.com' (sin los < >)
UPDATE configuracion_sistema 
SET valor = '<noreply@rapicredit.com>', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'from_email';

-- 4. Email Pruebas (OPCIONAL - solo necesario si modo_pruebas = true)
--    Si modo_pruebas = false, puedes omitir este UPDATE o dejarlo como está
--    Ejemplo: 'pruebas@ejemplo.com' (sin los < >)
UPDATE configuracion_sistema 
SET valor = '<pruebas@ejemplo.com>', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'email_pruebas';

-- ============================================
-- VERIFICAR DESPUÉS DE ACTUALIZAR
-- ============================================
SELECT 
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE 
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        AND (valor IS NULL OR valor = '' OR valor LIKE '<%>')
        THEN '❌ PENDIENTE: Reemplaza el valor'
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        THEN '✅ Configurado'
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

