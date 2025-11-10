-- ============================================
-- CONFIGURACIÓN FINAL CON VALORES REALES
-- Ejecutar estos comandos en DBeaver
-- ============================================

-- ============================================
-- ACTUALIZAR CONFIGURACIÓN EMAIL
-- ============================================

-- 1. SMTP User
UPDATE configuracion_sistema 
SET valor = 'pafo.kampei@gmail.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

-- 2. SMTP Password (App Password de Gmail)
UPDATE configuracion_sistema 
SET valor = 'vh$8vmJ51zVuZrK&QK51ZWGK4ck!rMR#aUPsmH4YNsXm7Z64nB', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

-- 3. From Email (usar el mismo email como remitente)
UPDATE configuracion_sistema 
SET valor = 'pafo.kampei@gmail.com', actualizado_en = NOW()
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

