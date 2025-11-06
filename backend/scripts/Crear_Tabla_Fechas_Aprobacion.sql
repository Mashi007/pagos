-- ============================================================================
-- CREAR TABLA TEMPORAL PARA FECHAS DE APROBACIÓN
-- Esta tabla contendrá cédula y fecha_aprobacion para integrar a prestamos
-- ============================================================================

-- ============================================================================
-- PASO 1: Crear tabla temporal para fechas de aprobación
-- ============================================================================

-- Crear tabla temporal (si ya existe, la elimina primero)
DROP TABLE IF EXISTS fechas_aprobacion_temp CASCADE;

CREATE TABLE fechas_aprobacion_temp (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    fecha_aprobacion DATE NOT NULL,
    observaciones TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice para búsqueda rápida por cédula
CREATE INDEX idx_fechas_aprobacion_cedula ON fechas_aprobacion_temp(cedula);

-- ============================================================================
-- PASO 2: Estructura de ejemplo para cargar datos
-- ============================================================================

-- EJEMPLO: Insertar datos manualmente (reemplazar con tus datos reales)
/*
INSERT INTO fechas_aprobacion_temp (cedula, fecha_aprobacion, observaciones) VALUES
    ('V30596349', '2025-05-24', 'Fecha de aprobación original'),
    ('V12345678', '2025-05-25', 'Fecha de aprobación original'),
    -- Agregar más filas aquí...
;
*/

-- ============================================================================
-- PASO 3: Cargar datos desde CSV/Excel
-- ============================================================================

-- Si tienes un archivo CSV con formato: cedula,fecha_aprobacion
-- Usa este comando en psql (o equivalente en DBeaver):
/*
COPY fechas_aprobacion_temp (cedula, fecha_aprobacion)
FROM '/ruta/al/archivo/fechas_aprobacion.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
*/

-- ============================================================================
-- PASO 4: Verificar datos cargados
-- ============================================================================

-- Total de registros cargados
SELECT 
    'Total registros en tabla temporal' AS metrica,
    COUNT(*) AS cantidad
FROM fechas_aprobacion_temp;

-- Verificar duplicados por cédula
SELECT 
    cedula,
    COUNT(*) AS cantidad_veces,
    STRING_AGG(fecha_aprobacion::TEXT, ', ') AS fechas
FROM fechas_aprobacion_temp
GROUP BY cedula
HAVING COUNT(*) > 1;

-- Ejemplo de datos cargados (primeros 10)
SELECT 
    id,
    cedula,
    fecha_aprobacion,
    observaciones,
    fecha_carga
FROM fechas_aprobacion_temp
ORDER BY id
LIMIT 10;

-- ============================================================================
-- PASO 5: Verificar coincidencias con préstamos existentes
-- ============================================================================

-- Cuántos préstamos coinciden con las cédulas en la tabla temporal
SELECT 
    'Préstamos que coinciden con tabla temporal' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad_prestamos
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO';

-- Préstamos que NO coinciden (cédulas en tabla temporal pero no en prestamos)
SELECT 
    'Cédulas en tabla temporal SIN préstamos' AS metrica,
    COUNT(DISTINCT f.cedula) AS cantidad
FROM fechas_aprobacion_temp f
LEFT JOIN prestamos p ON f.cedula = p.cedula AND p.estado = 'APROBADO'
WHERE p.id IS NULL;

-- Préstamos aprobados que NO están en tabla temporal (necesitan fecha)
SELECT 
    'Préstamos aprobados SIN fecha en tabla temporal' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND f.id IS NULL;

-- ============================================================================
-- NOTAS IMPORTANTES:
-- ============================================================================
-- 1. La tabla fechas_aprobacion_temp es temporal - puedes eliminarla después
-- 2. Si una cédula tiene múltiples préstamos, todos usarán la misma fecha
-- 3. Si hay duplicados en la tabla temporal, se usará la primera fecha encontrada
-- 4. Después de actualizar prestamos, puedes eliminar la tabla temporal
-- ============================================================================

