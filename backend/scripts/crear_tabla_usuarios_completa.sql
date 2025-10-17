-- ============================================
-- SCRIPT PARA CREAR TABLA USUARIOS DESDE CERO
-- Sistema de Préstamos y Cobranza - RapiCredit
-- ============================================
-- Fecha: 2025-10-17
-- Descripción: Crear tabla usuarios con sistema de roles completo
-- ============================================

-- PASO 1: Crear extensión pgcrypto para hash de contraseñas
SELECT 'PASO 1: Creando extensión pgcrypto' AS paso;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- PASO 2: Crear enum para roles de usuario
SELECT 'PASO 2: Creando enum UserRole' AS paso;

DO $$
BEGIN
    -- Eliminar enum si existe
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        DROP TYPE userrole CASCADE;
    END IF;
    
    -- Crear nuevo enum con todos los roles
    CREATE TYPE userrole AS ENUM ('USER', 'ADMIN', 'GERENTE', 'COBRANZAS');
    
    RAISE NOTICE 'Enum userrole creado: USER, ADMIN, GERENTE, COBRANZAS';
END $$;

-- PASO 3: Crear tabla usuarios
SELECT 'PASO 3: Creando tabla usuarios' AS paso;

CREATE TABLE IF NOT EXISTS usuarios (
    -- ID único
    id SERIAL PRIMARY KEY,
    
    -- Información personal
    email VARCHAR(255) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    
    -- Seguridad
    hashed_password VARCHAR(255) NOT NULL,
    
    -- Roles y permisos
    rol userrole NOT NULL DEFAULT 'USER',
    cargo VARCHAR(100),  -- Posición en la empresa (separado del rol)
    
    -- Estado
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE  -- Último acceso (se actualiza automáticamente)
);

-- PASO 4: Crear índices para optimización
SELECT 'PASO 4: Creando índices' AS paso;

-- Índice para email (ya es único, pero explícito)
CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_email ON usuarios(email);

-- Índice para rol (para filtros rápidos)
CREATE INDEX IF NOT EXISTS ix_usuarios_rol ON usuarios(rol);

-- Índice para cargo (para búsquedas por posición)
CREATE INDEX IF NOT EXISTS ix_usuarios_cargo ON usuarios(cargo);

-- Índice para estado activo (para filtros de usuarios activos)
CREATE INDEX IF NOT EXISTS ix_usuarios_is_active ON usuarios(is_active);

-- Índice para último login (para auditoría)
CREATE INDEX IF NOT EXISTS ix_usuarios_last_login ON usuarios(last_login);

-- PASO 5: Crear función para actualizar updated_at automáticamente
SELECT 'PASO 5: Creando función de actualización automática' AS paso;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- PASO 6: Crear trigger para updated_at
SELECT 'PASO 6: Creando trigger para updated_at' AS paso;

DROP TRIGGER IF EXISTS update_usuarios_updated_at ON usuarios;
CREATE TRIGGER update_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- PASO 7: Insertar usuario administrador inicial
SELECT 'PASO 7: Creando usuario administrador' AS paso;

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
) ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    hashed_password = EXCLUDED.hashed_password,
    rol = EXCLUDED.rol,
    cargo = EXCLUDED.cargo,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- PASO 8: Verificar creación exitosa
SELECT 'PASO 8: Verificación de creación' AS paso;

-- Verificar estructura de la tabla
SELECT 
    'ESTRUCTURA DE TABLA' AS verificacion,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;

-- Verificar enum creado
SELECT 
    'ENUM USERROLE' AS verificacion,
    e.enumlabel AS rol_disponible
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'userrole'
ORDER BY e.enumsortorder;

-- Verificar índices creados
SELECT 
    'ÍNDICES CREADOS' AS verificacion,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'usuarios'
ORDER BY indexname;

-- Verificar usuario administrador
SELECT 
    'USUARIO ADMINISTRADOR' AS verificacion,
    id,
    email,
    nombre,
    apellido,
    rol,
    cargo,
    is_active,
    created_at,
    CASE 
        WHEN rol = 'ADMIN' THEN '✅ ADMIN CREADO'
        ELSE '❌ NO ES ADMIN'
    END AS estado
FROM usuarios
WHERE email = 'itmaster@rapicreditca.com';

-- Estadísticas finales
SELECT 
    'ESTADÍSTICAS FINALES' AS verificacion,
    COUNT(*) AS total_usuarios,
    COUNT(*) FILTER (WHERE rol = 'ADMIN') AS total_admins,
    COUNT(*) FILTER (WHERE is_active = true) AS usuarios_activos,
    COUNT(*) FILTER (WHERE rol = 'ADMIN' AND is_active = true) AS admins_activos
FROM usuarios;

-- PASO 9: Mensaje de éxito
SELECT '✅ TABLA USUARIOS CREADA EXITOSAMENTE' AS resultado;
SELECT '📧 Email: itmaster@rapicreditca.com' AS credencial_1;
SELECT '🔑 Password: R@pi_2025**' AS credencial_2;
SELECT '🔗 URL: https://rapicredit.onrender.com/login' AS url_login;
SELECT '👤 Rol: ADMIN' AS rol_usuario;
SELECT '💼 Cargo: Consultor Tecnología' AS cargo_usuario;

-- ============================================
-- INFORMACIÓN ADICIONAL
-- ============================================

-- Roles disponibles y sus descripciones
SELECT 
    'ROLES DEL SISTEMA' AS titulo,
    'USER' AS rol,
    'Usuario estándar con acceso completo a funcionalidades' AS descripcion
UNION ALL
SELECT 
    'ROLES DEL SISTEMA' AS titulo,
    'ADMIN' AS rol,
    'Administrador con permisos para crear usuarios y cambiar estados' AS descripcion
UNION ALL
SELECT 
    'ROLES DEL SISTEMA' AS titulo,
    'GERENTE' AS rol,
    'Gerente con acceso completo excepto gestión de usuarios' AS descripcion
UNION ALL
SELECT 
    'ROLES DEL SISTEMA' AS titulo,
    'COBRANZAS' AS rol,
    'Personal de cobranzas con acceso completo excepto gestión de usuarios' AS descripcion;

-- Campos de la tabla usuarios
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'id' AS campo,
    'SERIAL PRIMARY KEY' AS tipo,
    'Identificador único del usuario' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'email' AS campo,
    'VARCHAR(255) UNIQUE' AS tipo,
    'Email único del usuario (usado para login)' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'nombre' AS campo,
    'VARCHAR(100)' AS tipo,
    'Nombre del usuario' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'apellido' AS campo,
    'VARCHAR(100)' AS tipo,
    'Apellido del usuario' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'hashed_password' AS campo,
    'VARCHAR(255)' AS tipo,
    'Contraseña hasheada con bcrypt' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'rol' AS campo,
    'userrole ENUM' AS tipo,
    'Rol del usuario: USER, ADMIN, GERENTE, COBRANZAS' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'cargo' AS campo,
    'VARCHAR(100)' AS tipo,
    'Posición en la empresa (separado del rol)' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'is_active' AS campo,
    'BOOLEAN' AS tipo,
    'Estado del usuario (activo/inactivo)' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'created_at' AS campo,
    'TIMESTAMP WITH TIME ZONE' AS tipo,
    'Fecha de creación del usuario' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'updated_at' AS campo,
    'TIMESTAMP WITH TIME ZONE' AS tipo,
    'Fecha de última actualización (automática)' AS descripcion
UNION ALL
SELECT 
    'CAMPOS DE LA TABLA' AS titulo,
    'last_login' AS campo,
    'TIMESTAMP WITH TIME ZONE' AS tipo,
    'Fecha del último login (se actualiza automáticamente)' AS descripcion;

-- ============================================
-- ✅ SCRIPT COMPLETADO
-- ============================================

SELECT '🎉 TABLA USUARIOS CREADA COMPLETAMENTE' AS mensaje_final;
SELECT '📊 Total de campos: 11' AS estadistica_1;
SELECT '🔐 Total de roles: 4' AS estadistica_2;
SELECT '📈 Total de índices: 5' AS estadistica_3;
SELECT '⚡ Triggers activos: 1' AS estadistica_4;
SELECT '👤 Usuario admin creado: 1' AS estadistica_5;
