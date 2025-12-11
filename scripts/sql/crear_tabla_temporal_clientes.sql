-- =====================================================
-- CREAR TABLA TEMPORAL PARA IMPORTAR CLIENTES
-- Ejecutar antes de importar CSV en DBeaver
-- =====================================================

-- Eliminar tabla si existe
DROP TABLE IF EXISTS clientes_temp;

-- Crear tabla temporal con estructura compatible
CREATE TABLE clientes_temp (
    id INTEGER,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(15),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento DATE,
    ocupacion VARCHAR(100),
    estado VARCHAR(20),
    activo BOOLEAN,
    fecha_registro TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    usuario_registro VARCHAR(100),
    notas TEXT
);

-- Verificar que se creó correctamente
SELECT 
    'Tabla temporal creada' as estado,
    COUNT(*) as columnas
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'clientes_temp';

-- Mostrar estructura
SELECT 
    column_name as columna,
    data_type as tipo_dato,
    is_nullable as permite_null
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'clientes_temp'
ORDER BY ordinal_position;

-- =====================================================
-- INSTRUCCIONES PARA IMPORTAR CSV
-- =====================================================
-- 
-- 1. La tabla clientes_temp está lista
-- 2. En DBeaver:
--    - Click derecho en clientes_temp → Import Data
--    - Seleccionar tu archivo CSV
--    - Configurar mapeo de columnas
--    - Ejecutar importación
-- 3. Verificar datos importados:
--    SELECT COUNT(*) FROM clientes_temp;
-- 4. Continuar con el script de importación
-- =====================================================

