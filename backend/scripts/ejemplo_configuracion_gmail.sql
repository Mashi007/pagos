-- ============================================
-- EJEMPLO: CONFIGURACIÓN COMPLETA PARA GMAIL
-- Reemplaza los valores entre < > con tus datos reales
-- ============================================

-- Eliminar configuraciones existentes (opcional - solo si quieres empezar desde cero)
-- DELETE FROM configuracion_sistema WHERE categoria = 'EMAIL';

-- ============================================
-- CONFIGURACIÓN GMAIL - REEMPLAZA LOS VALORES
-- ============================================

-- 1. SMTP Host (Gmail)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_host', 'smtp.gmail.com', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 2. SMTP Port (587 para TLS - recomendado)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_port', '587', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 3. SMTP User (TU EMAIL DE GMAIL - reemplaza esto)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_user', '<TU-EMAIL@gmail.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 4. SMTP Password (TU APP PASSWORD - reemplaza esto)
-- IMPORTANTE: Gmail requiere App Password, NO tu contraseña normal
-- Cómo crear: https://support.google.com/accounts/answer/185833
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_password', '<TU-APP-PASSWORD>', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 5. From Email (email que aparecerá como remitente)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_email', '<noreply@rapicredit.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 6. From Name (nombre del remitente)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'from_name', 'RapiCredit', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 7. Use TLS (true para puerto 587)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'smtp_use_tls', 'true', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 8. Modo Pruebas (false = producción, true = desarrollo)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'modo_pruebas', 'false', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- 9. Email Pruebas (solo necesario si modo_pruebas = true)
INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
VALUES ('EMAIL', 'email_pruebas', '<pruebas@ejemplo.com>', 'STRING', true, NOW(), NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = NOW();

-- ============================================
-- VERIFICAR CONFIGURACIÓN INSERTADA
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
        THEN '❌ PENDIENTE: Reemplaza el valor entre < >'
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        THEN '✅ Configurado'
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;

