-- ============================================
-- VERIFICACIÓN CORRECTA DE CONFIGURACIÓN EMAIL
-- ============================================

SELECT 
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE 
        -- Para smtp_use_tls: debe ser 'true' o 'false'
        WHEN clave = 'smtp_use_tls' THEN
            CASE 
                WHEN valor IS NULL OR valor = '' THEN '❌ PROBLEMA: Vacío'
                WHEN valor NOT IN ('true', 'false') THEN '❌ PROBLEMA: Debe ser true o false'
                ELSE '✅ OK'
            END
        -- Para otros campos obligatorios: no debe ser NULL, vacío, o tener placeholders
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email') THEN
            CASE 
                WHEN valor IS NULL OR valor = '' THEN '❌ PROBLEMA: Vacío'
                WHEN valor LIKE '<%>' OR valor LIKE 'TU-%' THEN '❌ PROBLEMA: Tiene placeholder'
                ELSE '✅ OK'
            END
        -- Para campos opcionales
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

