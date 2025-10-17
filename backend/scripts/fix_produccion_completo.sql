-- ============================================
-- FIX COMPLETO PARA PRODUCCIÓN
-- Sistema de Préstamos y Cobranza - RapiCredit
-- ============================================
-- Fecha: 2025-10-17
-- Descripción: Migración de sistema de usuarios y roles
-- ============================================

-- PASO 1: Verificar estado actual de la tabla usuarios
SELECT 'PASO 1: Estado actual de tabla usuarios' AS paso;
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;

-- PASO 2: Verificar usuarios existentes
SELECT 'PASO 2: Usuarios existentes' AS paso;
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    rol, 
    is_active, 
    created_at
FROM usuarios;

-- ============================================
-- MIGRACIÓN: Actualizar sistema de roles
-- ============================================

-- PASO 3: Crear nuevo enum con roles actualizados (si no existe)
SELECT 'PASO 3: Actualizando enum de roles' AS paso;

DO $$
BEGIN
    -- Eliminar enum viejo si existe
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        -- Primero convertir columna a texto
        ALTER TABLE usuarios ALTER COLUMN rol TYPE VARCHAR(50);
        
        -- Eliminar enum viejo
        DROP TYPE userrole;
    END IF;
    
    -- Crear nuevo enum
    CREATE TYPE userrole AS ENUM ('USER', 'ADMIN', 'GERENTE', 'COBRANZAS');
    
    RAISE NOTICE 'Enum userrole creado correctamente';
END $$;

-- PASO 4: Agregar columna cargo si no existe
SELECT 'PASO 4: Agregando columna cargo' AS paso;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'cargo'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN cargo VARCHAR(100);
        RAISE NOTICE 'Columna cargo agregada';
    ELSE
        RAISE NOTICE 'Columna cargo ya existe';
    END IF;
END $$;

-- PASO 5: Convertir columna rol a usar el nuevo enum
SELECT 'PASO 5: Convirtiendo columna rol a usar nuevo enum' AS paso;

DO $$
BEGIN
    -- Actualizar valores existentes si es necesario
    UPDATE usuarios SET rol = 'USER' WHERE rol NOT IN ('USER', 'ADMIN', 'GERENTE', 'COBRANZAS');
    
    -- Convertir columna a usar enum
    ALTER TABLE usuarios ALTER COLUMN rol TYPE userrole USING rol::userrole;
    
    RAISE NOTICE 'Columna rol convertida a enum';
END $$;

-- PASO 6: Crear índice para cargo
SELECT 'PASO 6: Creando índice para cargo' AS paso;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'usuarios' AND indexname = 'ix_usuarios_cargo'
    ) THEN
        CREATE INDEX ix_usuarios_cargo ON usuarios(cargo);
        RAISE NOTICE 'Índice ix_usuarios_cargo creado';
    ELSE
        RAISE NOTICE 'Índice ix_usuarios_cargo ya existe';
    END IF;
END $$;

-- ============================================
-- CREAR USUARIO ADMINISTRADOR
-- ============================================

SELECT 'PASO 7: Creando usuario administrador' AS paso;

DO $$
BEGIN
    -- Verificar si el usuario ya existe
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'itmaster@rapicreditca.com') THEN
        INSERT INTO usuarios (
            email,
            nombre,
            apellido,
            hashed_password,
            rol,
            cargo,
            is_active,
            created_at
        ) VALUES (
            'itmaster@rapicreditca.com',
            'Daniel',
            'Casañas',
            crypt('R@pi_2025**', gen_salt('bf')),  -- Hash con bcrypt
            'ADMIN',
            'Consultor Tecnología',
            true,
            NOW()
        );
        RAISE NOTICE 'Usuario administrador creado: itmaster@rapicreditca.com';
    ELSE
        -- Si existe, actualizar a ADMIN con cargo
        UPDATE usuarios 
        SET 
            rol = 'ADMIN',
            cargo = 'Consultor Tecnología',
            is_active = true,
            hashed_password = crypt('R@pi_2025**', gen_salt('bf'))
        WHERE email = 'itmaster@rapicreditca.com';
        RAISE NOTICE 'Usuario administrador actualizado: itmaster@rapicreditca.com';
    END IF;
END $$;

-- ============================================
-- VERIFICACIÓN FINAL
-- ============================================

SELECT 'PASO 8: Verificación final' AS paso;

-- Verificar estructura actualizada
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;

-- Verificar enum actualizado
SELECT 
    e.enumlabel AS rol_valor
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'userrole'
ORDER BY e.enumsortorder;

-- Verificar usuario administrador
SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    cargo,
    is_active,
    created_at,
    CASE 
        WHEN rol = 'ADMIN' THEN '✅ ADMIN'
        ELSE '❌ NO ES ADMIN'
    END AS verificacion
FROM usuarios
WHERE email = 'itmaster@rapicreditca.com';

-- Estadísticas finales
SELECT 
    'RESUMEN FINAL' AS titulo,
    COUNT(*) AS total_usuarios,
    COUNT(*) FILTER (WHERE rol = 'ADMIN') AS total_admins,
    COUNT(*) FILTER (WHERE is_active = true) AS usuarios_activos,
    COUNT(*) FILTER (WHERE rol = 'ADMIN' AND is_active = true) AS admins_activos
FROM usuarios;

-- ============================================
-- ✅ MIGRACIÓN COMPLETADA
-- ============================================

SELECT '✅ MIGRACIÓN COMPLETADA EXITOSAMENTE' AS resultado;
SELECT '📧 Email: itmaster@rapicreditca.com' AS credencial_1;
SELECT '🔑 Password: R@pi_2025**' AS credencial_2;
SELECT '🔗 URL: https://rapicredit.onrender.com/login' AS url_login;

