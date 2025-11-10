-- ============================================
-- VERIFICAR Y CORREGIR from_email EN LA BASE DE DATOS
-- Si from_email está vacío pero smtp_user tiene valor, copiar smtp_user a from_email
-- ============================================

-- 1. Verificar estado actual
SELECT 
    clave,
    valor,
    CASE 
        WHEN clave = 'from_email' AND (valor IS NULL OR valor = '' OR valor = '<noreply@rapicredit.com>') THEN '❌ VACÍO O PLACEHOLDER'
        WHEN clave = 'from_email' THEN '✅ CONFIGURADO'
        ELSE 'N/A'
    END as estado_from_email,
    CASE 
        WHEN clave = 'smtp_user' AND (valor IS NULL OR valor = '' OR valor LIKE '<%' OR valor LIKE 'TU-%') THEN '❌ VACÍO O PLACEHOLDER'
        WHEN clave = 'smtp_user' THEN '✅ CONFIGURADO'
        ELSE 'N/A'
    END as estado_smtp_user
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
    AND (clave = 'from_email' OR clave = 'smtp_user')
ORDER BY clave;

-- 2. Si from_email está vacío pero smtp_user tiene valor, copiar smtp_user a from_email
UPDATE configuracion_sistema
SET valor = (
    SELECT valor 
    FROM configuracion_sistema cs2 
    WHERE cs2.categoria = 'EMAIL' 
        AND cs2.clave = 'smtp_user'
        AND cs2.valor IS NOT NULL 
        AND cs2.valor != '' 
        AND cs2.valor NOT LIKE '<%'
        AND cs2.valor NOT LIKE 'TU-%'
    LIMIT 1
),
actualizado_en = NOW()
WHERE categoria = 'EMAIL'
    AND clave = 'from_email'
    AND (
        valor IS NULL 
        OR valor = '' 
        OR valor = '<noreply@rapicredit.com>'
        OR valor LIKE '<%'
    )
    AND EXISTS (
        SELECT 1 
        FROM configuracion_sistema cs2 
        WHERE cs2.categoria = 'EMAIL' 
            AND cs2.clave = 'smtp_user'
            AND cs2.valor IS NOT NULL 
            AND cs2.valor != '' 
            AND cs2.valor NOT LIKE '<%'
            AND cs2.valor NOT LIKE 'TU-%'
    );

-- 3. Verificar resultado
SELECT 
    clave,
    valor,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
    AND (clave = 'from_email' OR clave = 'smtp_user')
ORDER BY clave;

