-- ============================================================================
-- CREAR TABLA TEMPORAL fechas_aprobacion_temp
-- Ejecuta este script completo
-- ============================================================================

-- Paso 1: Eliminar si existe (por si acaso)
DROP TABLE IF EXISTS fechas_aprobacion_temp CASCADE;

-- Paso 2: Crear la tabla
CREATE TABLE fechas_aprobacion_temp (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    fecha_aprobacion DATE NOT NULL,
    observaciones TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paso 3: Crear índice para búsqueda rápida
CREATE INDEX idx_fechas_aprobacion_cedula ON fechas_aprobacion_temp(cedula);

-- Paso 4: Verificar que se creó correctamente
SELECT 
    'Tabla creada exitosamente' AS resultado,
    COUNT(*) AS filas
FROM fechas_aprobacion_temp;

-- Paso 5: Ver la estructura de la tabla
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'fechas_aprobacion_temp'
ORDER BY ordinal_position;

