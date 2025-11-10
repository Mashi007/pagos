-- ============================================
-- SCRIPT SIMPLE DE VERIFICACIÓN EMAIL
-- Ejecutar en DBeaver - Copiar y pegar cada query
-- ============================================

-- ============================================
-- QUERY 1: Ver todas las configuraciones de EMAIL
-- ============================================
SELECT 
    id,
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    tipo_dato,
    creado_en,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

-- ============================================
-- QUERY 2: Verificar configuraciones faltantes
-- ============================================
SELECT 
    'smtp_host' AS configuracion,
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ OK' 
         ELSE '❌ FALTANTE' 
    END AS estado
UNION ALL
SELECT 'smtp_port',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ OK' 
         ELSE '❌ FALTANTE' 
    END
UNION ALL
SELECT 'smtp_user',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ OK' 
         ELSE '❌ FALTANTE' 
    END
UNION ALL
SELECT 'smtp_password',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ OK' 
         ELSE '❌ FALTANTE o VACÍO' 
    END
UNION ALL
SELECT 'from_email',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ OK' 
         ELSE '❌ FALTANTE' 
    END
UNION ALL
SELECT 'modo_pruebas',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND valor IS NOT NULL) 
         THEN '✅ OK' 
         ELSE '⚠️ OPCIONAL' 
    END
UNION ALL
SELECT 'email_pruebas',
    CASE 
        WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on'))
        AND NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != '')
        THEN '❌ REQUERIDO (modo_pruebas=true)'
        WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != '')
        THEN '✅ OK'
        ELSE '⚠️ OPCIONAL'
    END
ORDER BY configuracion;

-- ============================================
-- QUERY 3: Verificar problema crítico
-- modo_pruebas=true pero email_pruebas vacío
-- ============================================
SELECT 
    'PROBLEMA CRÍTICO' AS tipo,
    'modo_pruebas está activo pero email_pruebas no está configurado' AS descripcion,
    (SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas') AS modo_pruebas_valor,
    (SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas') AS email_pruebas_valor
WHERE EXISTS (
    SELECT 1 FROM configuracion_sistema 
    WHERE categoria = 'EMAIL' 
    AND clave = 'modo_pruebas' 
    AND LOWER(valor) IN ('true', '1', 'yes', 'on')
)
AND NOT EXISTS (
    SELECT 1 FROM configuracion_sistema 
    WHERE categoria = 'EMAIL' 
    AND clave = 'email_pruebas' 
    AND valor IS NOT NULL 
    AND valor != ''
);

-- ============================================
-- QUERY 4: Ver valores visibles (sin passwords)
-- ============================================
SELECT 
    clave,
    CASE 
        WHEN clave = 'smtp_host' THEN valor
        WHEN clave = 'smtp_port' THEN valor
        WHEN clave = 'smtp_user' THEN '*** (oculto)'
        WHEN clave = 'smtp_password' THEN '*** (oculto)'
        WHEN clave = 'from_email' THEN valor
        WHEN clave = 'from_name' THEN valor
        WHEN clave = 'smtp_use_tls' THEN valor
        WHEN clave = 'modo_pruebas' THEN valor
        WHEN clave = 'email_pruebas' THEN valor
        ELSE valor
    END AS valor
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

