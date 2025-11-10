-- ============================================
-- SCRIPT PARA ACTUALIZAR CONFIGURACIÓN EMAIL
-- Si ya existe, la actualiza; si no, la crea
-- ============================================

-- IMPORTANTE: Reemplaza los valores entre < > con tus datos reales

-- ============================================
-- ACTUALIZAR O CREAR CONFIGURACIONES
-- ============================================

-- 1. SMTP Host
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host') THEN
        UPDATE configuracion_sistema 
        SET valor = 'smtp.gmail.com', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'smtp_host';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'smtp_host', 'smtp.gmail.com', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 2. SMTP Port
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_port') THEN
        UPDATE configuracion_sistema 
        SET valor = '587', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'smtp_port';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'smtp_port', '587', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 3. SMTP User (REEMPLAZA <TU-EMAIL@gmail.com>)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_user') THEN
        UPDATE configuracion_sistema 
        SET valor = '<TU-EMAIL@gmail.com>', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'smtp_user';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'smtp_user', '<TU-EMAIL@gmail.com>', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 4. SMTP Password (REEMPLAZA <TU-APP-PASSWORD>)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_password') THEN
        UPDATE configuracion_sistema 
        SET valor = '<TU-APP-PASSWORD>', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'smtp_password';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'smtp_password', '<TU-APP-PASSWORD>', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 5. From Email (REEMPLAZA <noreply@rapicredit.com>)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_email') THEN
        UPDATE configuracion_sistema 
        SET valor = '<noreply@rapicredit.com>', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'from_email';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'from_email', '<noreply@rapicredit.com>', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 6. From Name
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'from_name') THEN
        UPDATE configuracion_sistema 
        SET valor = 'RapiCredit', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'from_name';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'from_name', 'RapiCredit', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 7. Use TLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls') THEN
        UPDATE configuracion_sistema 
        SET valor = 'true', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'smtp_use_tls';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'smtp_use_tls', 'true', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 8. Modo Pruebas
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas') THEN
        UPDATE configuracion_sistema 
        SET valor = 'false', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'modo_pruebas';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'modo_pruebas', 'false', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

-- 9. Email Pruebas
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'email_pruebas') THEN
        UPDATE configuracion_sistema 
        SET valor = '<pruebas@ejemplo.com>', actualizado_en = NOW()
        WHERE categoria = 'EMAIL' AND clave = 'email_pruebas';
    ELSE
        INSERT INTO configuracion_sistema (categoria, clave, valor, tipo_dato, visible_frontend, creado_en, actualizado_en)
        VALUES ('EMAIL', 'email_pruebas', '<pruebas@ejemplo.com>', 'STRING', true, NOW(), NOW());
    END IF;
END $$;

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

