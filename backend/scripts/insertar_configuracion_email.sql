-- ============================================
-- SCRIPT PARA INSERTAR CONFIGURACIÓN DE EMAIL
-- Ejecutar en DBeaver después de completar los valores
-- ============================================

-- IMPORTANTE: Reemplaza los valores entre < > con tus datos reales antes de ejecutar

-- ============================================
-- CONFIGURACIÓN BÁSICA SMTP
-- ============================================

-- 1. SMTP Host (ejemplo para Gmail)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_host', '<smtp.gmail.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 2. SMTP Port (587 para TLS, 465 para SSL)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_port', '<587>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 3. SMTP User (tu email completo)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_user', '<tu-email@gmail.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 4. SMTP Password (App Password de Gmail o contraseña normal)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_password', '<tu-app-password>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 5. From Email (email remitente)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_email', '<noreply@rapicredit.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 6. From Name (nombre del remitente)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_name', 'RapiCredit', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 7. Use TLS (true para puerto 587, false para puerto 465 con SSL)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_use_tls', 'true', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- CONFIGURACIÓN DE MODO PRUEBAS
-- ============================================

-- 8. Modo Pruebas (true = redirige todos los emails a email_pruebas, false = envía a destinatarios reales)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'modo_pruebas', '<false>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 9. Email Pruebas (solo necesario si modo_pruebas = true)
-- Si modo_pruebas = false, puedes omitir este INSERT o dejarlo vacío
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'email_pruebas', '<pruebas@ejemplo.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- VERIFICACIÓN DESPUÉS DE INSERTAR
-- ============================================

-- Ejecutar esta consulta después de insertar para verificar:
SELECT 
    clave,
    CASE 
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE 
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        AND (valor IS NULL OR valor = '' OR valor LIKE '<%>')
        THEN '❌ PENDIENTE DE CONFIGURAR'
        ELSE '✅ Configurado'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

-- ============================================
-- NOTAS IMPORTANTES:
-- ============================================
-- 1. Para Gmail:
--    - smtp_host: smtp.gmail.com
--    - smtp_port: 587 (TLS) o 465 (SSL)
--    - smtp_use_tls: true (para puerto 587) o false (para puerto 465)
--    - smtp_user: tu email completo (ej: usuario@gmail.com)
--    - smtp_password: App Password (NO tu contraseña normal)
--       * Cómo crear App Password: https://support.google.com/accounts/answer/185833
--
-- 2. Para otros proveedores:
--    - Outlook/Hotmail: smtp-mail.outlook.com, puerto 587
--    - Yahoo: smtp.mail.yahoo.com, puerto 587
--    - Otros: consulta la documentación de tu proveedor
--
-- 3. Modo Pruebas:
--    - true: Todos los emails se redirigen a email_pruebas (útil para desarrollo)
--    - false: Los emails se envían a los destinatarios reales (producción)
--
-- 4. Seguridad:
--    - NUNCA compartas tu smtp_password
--    - Usa App Passwords en lugar de contraseñas normales cuando sea posible
--    - Considera usar variables de entorno para producción

