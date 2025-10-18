-- Script para verificar la estructura de la tabla concesionarios
-- Este script debe ejecutarse directamente en la base de datos

-- Verificar si la tabla existe
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'concesionarios';

-- Verificar la estructura de la tabla concesionarios
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'concesionarios'
ORDER BY ordinal_position;

-- Si la tabla no existe, crearla con la estructura correcta
CREATE TABLE IF NOT EXISTS concesionarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    direccion TEXT,
    telefono VARCHAR(20),
    email VARCHAR(255),
    responsable VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Crear índices
CREATE INDEX IF NOT EXISTS idx_concesionarios_nombre ON concesionarios(nombre);
CREATE INDEX IF NOT EXISTS idx_concesionarios_activo ON concesionarios(activo);

-- Insertar datos de prueba si la tabla está vacía
INSERT INTO concesionarios (nombre, direccion, telefono, email, responsable, activo)
VALUES 
    ('Concesionario Test 1', 'Dirección Test 1', '123456789', 'test1@test.com', 'Responsable 1', true),
    ('Concesionario Test 2', 'Dirección Test 2', '987654321', 'test2@test.com', 'Responsable 2', true)
ON CONFLICT (nombre) DO NOTHING;
