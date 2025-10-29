-- ============================================
-- SCRIPT DE ACTUALIZACIÓN: TABLAS DE CATÁLOGOS
-- ============================================
-- Fecha: 2025-10-30
-- Descripción: Actualiza/crea las tablas concesionarios, analistas y modelos_vehiculos
-- Ejecutar en: DBeaver (Producción)
-- ============================================

-- ============================================
-- TABLA: concesionarios
-- ============================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS concesionarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agregar columnas si no existen
DO $$
BEGIN
    -- Agregar nombre si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'concesionarios' AND column_name = 'nombre'
    ) THEN
        ALTER TABLE concesionarios ADD COLUMN nombre VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    
    -- Agregar activo si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'concesionarios' AND column_name = 'activo'
    ) THEN
        ALTER TABLE concesionarios ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true;
    END IF;
    
    -- Agregar created_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'concesionarios' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE concesionarios ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Agregar updated_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'concesionarios' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE concesionarios ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Crear índices si no existen
CREATE INDEX IF NOT EXISTS ix_concesionarios_nombre ON concesionarios(nombre);

-- Actualizar registros existentes sin timestamps
UPDATE concesionarios 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at IS NULL;

UPDATE concesionarios 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at IS NULL;

-- ============================================
-- TABLA: analistas
-- ============================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS analistas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agregar columnas si no existen
DO $$
BEGIN
    -- Agregar nombre si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'analistas' AND column_name = 'nombre'
    ) THEN
        ALTER TABLE analistas ADD COLUMN nombre VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    
    -- Agregar activo si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'analistas' AND column_name = 'activo'
    ) THEN
        ALTER TABLE analistas ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true;
    END IF;
    
    -- Agregar created_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'analistas' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE analistas ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Agregar updated_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'analistas' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE analistas ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Crear índices si no existen
CREATE INDEX IF NOT EXISTS ix_analistas_nombre ON analistas(nombre);

-- Actualizar registros existentes sin timestamps
UPDATE analistas 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at IS NULL;

UPDATE analistas 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at IS NULL;

-- ============================================
-- TABLA: modelos_vehiculos
-- ============================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS modelos_vehiculos (
    id SERIAL PRIMARY KEY,
    modelo VARCHAR(100) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agregar columnas si no existen
DO $$
BEGIN
    -- Agregar modelo si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'modelos_vehiculos' AND column_name = 'modelo'
    ) THEN
        ALTER TABLE modelos_vehiculos ADD COLUMN modelo VARCHAR(100) NOT NULL DEFAULT '';
    END IF;
    
    -- Agregar activo si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'modelos_vehiculos' AND column_name = 'activo'
    ) THEN
        ALTER TABLE modelos_vehiculos ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true;
    END IF;
    
    -- Agregar created_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'modelos_vehiculos' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE modelos_vehiculos ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Agregar updated_at si no existe
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'modelos_vehiculos' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE modelos_vehiculos ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Crear índices si no existen
CREATE INDEX IF NOT EXISTS ix_modelos_vehiculos_modelo ON modelos_vehiculos(modelo);
CREATE INDEX IF NOT EXISTS ix_modelos_vehiculos_activo ON modelos_vehiculos(activo);

-- Crear constraint único si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_constraint 
        WHERE conname = 'uq_modelos_vehiculos_modelo'
    ) THEN
        ALTER TABLE modelos_vehiculos 
        ADD CONSTRAINT uq_modelos_vehiculos_modelo UNIQUE (modelo);
    END IF;
END $$;

-- Actualizar registros existentes sin timestamps
UPDATE modelos_vehiculos 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at IS NULL;

UPDATE modelos_vehiculos 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at IS NULL;

-- ============================================
-- VERIFICACIÓN
-- ============================================
-- Verificar estructura de las tablas
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name IN ('concesionarios', 'analistas', 'modelos_vehiculos')
ORDER BY table_name, ordinal_position;

-- Verificar índices
SELECT 
    tablename,
    indexname
FROM pg_indexes
WHERE tablename IN ('concesionarios', 'analistas', 'modelos_vehiculos')
ORDER BY tablename, indexname;

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

