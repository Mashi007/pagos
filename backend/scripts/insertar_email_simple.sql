-- ============================================
-- SCRIPT SIMPLE PARA INSERTAR CONFIGURACIÓN EMAIL
-- Funciona sin necesidad de constraint única
-- ============================================

-- IMPORTANTE: Reemplaza los valores entre < > con tus datos reales

-- ============================================
-- CONFIGURACIÓN GMAIL
-- ============================================

-- 1. SMTP Host
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_host', 'smtp.gmail.com', 'STRING', true, NOW(), NOW());

-- 2. SMTP Port
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_port', '587', 'STRING', true, NOW(), NOW());

-- 3. SMTP User (REEMPLAZA <TU-EMAIL@gmail.com>)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_user', '<TU-EMAIL@gmail.com>', 'STRING', true, NOW(), NOW());

-- 4. SMTP Password (REEMPLAZA <TU-APP-PASSWORD>)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_password', '<TU-APP-PASSWORD>', 'STRING', true, NOW(), NOW());

-- 5. From Email (REEMPLAZA <noreply@rapicredit.com>)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_email', '<noreply@rapicredit.com>', 'STRING', true, NOW(), NOW());

-- 6. From Name
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_name', 'RapiCredit', 'STRING', true, NOW(), NOW());

-- 7. Use TLS
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_use_tls', 'true', 'STRING', true, NOW(), NOW());

-- 8. Modo Pruebas (false = producción, true = desarrollo)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'modo_pruebas', 'false', 'STRING', true, NOW(), NOW());

-- 9. Email Pruebas (opcional, solo si modo_pruebas = true)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'email_pruebas', '<pruebas@ejemplo.com>', 'STRING', true, NOW(), NOW());

-- ============================================
-- VERIFICAR DESPUÉS DE INSERTAR
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

