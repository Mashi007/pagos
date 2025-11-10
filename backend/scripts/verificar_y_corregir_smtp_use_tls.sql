-- ============================================
-- VERIFICAR Y CORREGIR smtp_use_tls
-- ============================================

-- 1. Verificar valor actual
SELECT 
    clave,
    valor,
    typeof(valor) as tipo_valor,
    length(valor) as longitud
FROM configuracion_sistema 
WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls';

-- 2. Actualizar a string 'true' explícitamente
UPDATE configuracion_sistema 
SET valor = 'true', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls';

-- 3. Verificar después de actualizar
SELECT 
    clave,
    valor,
    typeof(valor) as tipo_valor,
    CASE 
        WHEN valor = 'true' THEN '✅ Correcto'
        ELSE '❌ Incorrecto'
    END AS estado
FROM configuracion_sistema 
WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls';

