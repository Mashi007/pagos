-- ============================================
-- SCRIPT DE VERIFICACIÓN DE CONFIGURACIÓN EMAIL
-- Para ejecutar en DBeaver o cualquier cliente SQL
-- ============================================

-- 1. Verificar todas las configuraciones de EMAIL
SELECT 
    id,
    categoria,
    clave,
    valor,
    tipo_dato,
    visible_frontend,
    creado_en,
    actualizado_en
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

-- 2. Verificar si existen todas las configuraciones necesarias
SELECT 
    'smtp_host' AS configuracion,
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host') 
         THEN '✅ Configurado' 
         ELSE '❌ FALTANTE' 
    END AS estado,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host'), 'NO CONFIGURADO') AS valor
UNION ALL
SELECT 
    'smtp_port',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port') 
         THEN '✅ Configurado' 
         ELSE '❌ FALTANTE' 
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    'smtp_user',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user') 
         THEN '✅ Configurado' 
         ELSE '❌ FALTANTE' 
    END,
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user' AND valor IS NOT NULL AND valor != '') 
         THEN '*** (oculto)' 
         ELSE 'NO CONFIGURADO' 
    END
UNION ALL
SELECT 
    'smtp_password',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password' AND valor IS NOT NULL AND valor != '') 
         THEN '✅ Configurado' 
         ELSE '❌ FALTANTE o VACÍO' 
    END,
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password' AND valor IS NOT NULL AND valor != '') 
         THEN '*** (oculto - ' || LENGTH((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password')) || ' caracteres)' 
         ELSE 'NO CONFIGURADO' 
    END
UNION ALL
SELECT 
    'from_email',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email') 
         THEN '✅ Configurado' 
         ELSE '❌ FALTANTE' 
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    'from_name',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_name') 
         THEN '✅ Configurado' 
         ELSE '⚠️ OPCIONAL' 
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_name'), 'NO CONFIGURADO (usará valor por defecto)')
UNION ALL
SELECT 
    'smtp_use_tls',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls') 
         THEN '✅ Configurado' 
         ELSE '⚠️ OPCIONAL' 
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls'), 'NO CONFIGURADO (usará true por defecto)')
UNION ALL
SELECT 
    'modo_pruebas',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas') 
         THEN '✅ Configurado' 
         ELSE '⚠️ OPCIONAL' 
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas'), 'NO CONFIGURADO (usará true por defecto)')
UNION ALL
SELECT 
    'email_pruebas',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != '') 
         THEN CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on'))
                   THEN '✅ Configurado (requerido si modo_pruebas=true)'
                   ELSE '✅ Configurado (no requerido si modo_pruebas=false)'
              END
         ELSE CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on'))
                   THEN '❌ FALTANTE (REQUERIDO si modo_pruebas=true)'
                   ELSE '⚠️ OPCIONAL (no requerido si modo_pruebas=false)'
              END
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas'), 'NO CONFIGURADO')
ORDER BY configuracion;

-- 3. Resumen de configuración (valores visibles)
SELECT 
    'RESUMEN DE CONFIGURACIÓN EMAIL' AS titulo,
    '' AS valor
UNION ALL
SELECT 
    'SMTP Server:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    'SMTP Port:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    'SMTP User:',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user' AND valor IS NOT NULL AND valor != '') 
         THEN '*** CONFIGURADO' 
         ELSE 'NO CONFIGURADO' 
    END
UNION ALL
SELECT 
    'SMTP Password:',
    CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password' AND valor IS NOT NULL AND valor != '') 
         THEN '*** CONFIGURADO (' || LENGTH((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password')) || ' caracteres)' 
         ELSE 'NO CONFIGURADO' 
    END
UNION ALL
SELECT 
    'From Email:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    'From Name:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_name'), 'NO CONFIGURADO (usará RapiCredit)')
UNION ALL
SELECT 
    'Use TLS:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls'), 'NO CONFIGURADO (usará true)')
UNION ALL
SELECT 
    'Modo Pruebas:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas'), 'NO CONFIGURADO (usará true)')
UNION ALL
SELECT 
    'Email Pruebas:',
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas'), 'NO CONFIGURADO')
UNION ALL
SELECT 
    '---',
    '---'
UNION ALL
SELECT 
    '⚠️ VALIDACIONES:',
    ''
UNION ALL
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host' AND valor IS NOT NULL AND valor != '')
        THEN '❌ smtp_host NO CONFIGURADO'
        ELSE '✅ smtp_host configurado'
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host'), '')
UNION ALL
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port' AND valor IS NOT NULL AND valor != '')
        THEN '❌ smtp_port NO CONFIGURADO'
        WHEN (SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port')::text NOT SIMILAR TO '[0-9]+'
        THEN '❌ smtp_port INVÁLIDO (debe ser numérico)'
        ELSE '✅ smtp_port configurado'
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port'), '')
UNION ALL
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user' AND valor IS NOT NULL AND valor != '')
        THEN '❌ smtp_user NO CONFIGURADO'
        ELSE '✅ smtp_user configurado'
    END,
    '*** (oculto)'
UNION ALL
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password' AND valor IS NOT NULL AND valor != '')
        THEN '❌ smtp_password NO CONFIGURADO o VACÍO'
        ELSE '✅ smtp_password configurado'
    END,
    '*** (oculto)'
UNION ALL
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email' AND valor IS NOT NULL AND valor != '')
        THEN '❌ from_email NO CONFIGURADO'
        ELSE '✅ from_email configurado'
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email'), '')
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on'))
        AND NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != '')
        THEN '❌ PROBLEMA: modo_pruebas=true pero email_pruebas NO CONFIGURADO'
        WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on'))
        THEN '⚠️ modo_pruebas ACTIVO - emails se redirigirán a email_pruebas'
        ELSE '✅ modo_pruebas INACTIVO - emails se enviarán a destinatarios reales'
    END,
    COALESCE((SELECT valor FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas'), 'NO CONFIGURADO');

-- 4. Verificar si hay configuraciones duplicadas (no debería haber)
SELECT 
    categoria,
    clave,
    COUNT(*) AS cantidad,
    string_agg(id::text, ', ' ORDER BY id) AS ids,
    string_agg(valor, ' | ' ORDER BY id) AS valores
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
GROUP BY categoria, clave
HAVING COUNT(*) > 1;

-- 5. Verificar valores problemáticos
SELECT 
    'CONFIGURACIONES PROBLEMÁTICAS' AS tipo,
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE 
        WHEN clave = 'smtp_port' AND (valor !~ '^[0-9]+$' OR valor::integer NOT BETWEEN 1 AND 65535)
        THEN 'Puerto inválido (debe ser 1-65535)'
        WHEN clave = 'smtp_password' AND (valor IS NULL OR valor = '')
        THEN 'Contraseña vacía'
        WHEN clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on')
             AND NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != '')
        THEN 'modo_pruebas activo sin email_pruebas configurado'
        WHEN clave = 'smtp_use_tls' AND LOWER(valor) NOT IN ('true', '1', 'yes', 'on', 'false', '0', 'no', 'off')
        THEN 'Valor inválido para smtp_use_tls'
        ELSE NULL
    END AS problema
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
AND (
    (clave = 'smtp_port' AND (valor !~ '^[0-9]+$' OR valor::integer NOT BETWEEN 1 AND 65535))
    OR (clave = 'smtp_password' AND (valor IS NULL OR valor = ''))
    OR (clave = 'modo_pruebas' AND LOWER(valor) IN ('true', '1', 'yes', 'on')
        AND NOT EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas' AND valor IS NOT NULL AND valor != ''))
    OR (clave = 'smtp_use_tls' AND LOWER(valor) NOT IN ('true', '1', 'yes', 'on', 'false', '0', 'no', 'off'))
)
ORDER BY clave;

-- 6. QUERY SIMPLE - Ver todas las configuraciones de email (ejecutar primero)
-- SELECT * FROM configuracion_sistema WHERE categoria = 'EMAIL' ORDER BY clave;

