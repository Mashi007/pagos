-- ============================================================================
-- SCRIPT: CREAR Y MANTENER TABLA MONITOREO
-- ============================================================================
-- Descripción: Crea una tabla "Monitoreo" que extrae y actualiza la columna
--              "cedula" del módulo Clientes cada vez que se ejecuta
--
-- Uso: 
--   1. Ejecutar la sección 1 para crear la tabla
--   2. Ejecutar la sección 2 para sincronizar/actualizar datos
--   3. Ejecutar la sección 3 para verificar datos
--
-- Autor: Sistema de Pagos
-- Fecha: 2025
-- ============================================================================

-- ============================================================================
-- SECCIÓN 1: CREAR TABLA MONITOREO
-- ============================================================================
-- Esta sección crea la tabla Monitoreo si no existe

-- Eliminar tabla si ya existe (cuidado: esto borra todos los datos)
-- Descomenta solo si quieres recrear la tabla desde cero
-- DROP TABLE IF EXISTS monitoreo;

-- Crear tabla Monitoreo
CREATE TABLE IF NOT EXISTS monitoreo (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL UNIQUE,
    fecha_extraccion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    observaciones TEXT,
    CONSTRAINT monitoreo_cedula_unique UNIQUE (cedula)
);

-- Crear índice para búsquedas rápidas por cédula
CREATE INDEX IF NOT EXISTS idx_monitoreo_cedula ON monitoreo(cedula);

-- Crear índice para búsquedas por fecha de actualización
CREATE INDEX IF NOT EXISTS idx_monitoreo_fecha_actualizacion ON monitoreo(fecha_actualizacion);

-- Comentarios en la tabla
COMMENT ON TABLE monitoreo IS 'Tabla de monitoreo que almacena cédulas extraídas del módulo Clientes';
COMMENT ON COLUMN monitoreo.id IS 'ID único del registro';
COMMENT ON COLUMN monitoreo.cedula IS 'Cédula extraída de la tabla clientes';
COMMENT ON COLUMN monitoreo.fecha_extraccion IS 'Fecha y hora en que se extrajo la cédula por primera vez';
COMMENT ON COLUMN monitoreo.fecha_actualizacion IS 'Fecha y hora de la última actualización';
COMMENT ON COLUMN monitoreo.activo IS 'Indica si el registro está activo';
COMMENT ON COLUMN monitoreo.observaciones IS 'Observaciones adicionales';

-- ============================================================================
-- SECCIÓN 2: SINCRONIZAR/ACTUALIZAR DATOS
-- ============================================================================
-- Esta sección sincroniza la tabla Monitoreo con la tabla clientes
-- Ejecutar esta sección cada vez que quieras actualizar los datos

-- Paso 1: Insertar nuevas cédulas que no existen en Monitoreo
INSERT INTO monitoreo (cedula, fecha_extraccion, fecha_actualizacion, activo)
SELECT 
    c.cedula,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    CASE 
        WHEN c.activo = TRUE AND c.estado = 'ACTIVO' THEN TRUE
        ELSE FALSE
    END as activo
FROM clientes c
WHERE NOT EXISTS (
    SELECT 1 
    FROM monitoreo m 
    WHERE m.cedula = c.cedula
)
ON CONFLICT (cedula) DO NOTHING;

-- Paso 2: Actualizar registros existentes
-- Actualizar fecha_actualizacion y estado activo para cédulas que ya existen
UPDATE monitoreo m
SET 
    fecha_actualizacion = CURRENT_TIMESTAMP,
    activo = CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM clientes c 
            WHERE c.cedula = m.cedula 
            AND c.activo = TRUE 
            AND c.estado = 'ACTIVO'
        ) THEN TRUE
        ELSE FALSE
    END
WHERE EXISTS (
    SELECT 1 
    FROM clientes c 
    WHERE c.cedula = m.cedula
);

-- Paso 3: Marcar como inactivas las cédulas que ya no existen en clientes
-- (Opcional: Descomenta si quieres marcar como inactivas las cédulas eliminadas)
/*
UPDATE monitoreo m
SET 
    activo = FALSE,
    fecha_actualizacion = CURRENT_TIMESTAMP,
    observaciones = COALESCE(observaciones || '; ', '') || 
                   'Cliente eliminado de la tabla clientes'
WHERE NOT EXISTS (
    SELECT 1 
    FROM clientes c 
    WHERE c.cedula = m.cedula
);
*/

-- ============================================================================
-- SECCIÓN 3: VERIFICAR DATOS
-- ============================================================================
-- Esta sección contiene queries para verificar los datos sincronizados

-- 3.1. Contar total de registros en Monitoreo
SELECT 
    COUNT(*) as total_registros,
    COUNT(*) FILTER (WHERE activo = TRUE) as registros_activos,
    COUNT(*) FILTER (WHERE activo = FALSE) as registros_inactivos
FROM monitoreo;

-- 3.2. Comparar con tabla clientes
SELECT 
    'clientes' as tabla,
    COUNT(*) as total_cedulas,
    COUNT(DISTINCT cedula) as cedulas_unicas
FROM clientes
UNION ALL
SELECT 
    'monitoreo' as tabla,
    COUNT(*) as total_cedulas,
    COUNT(DISTINCT cedula) as cedulas_unicas
FROM monitoreo;

-- 3.3. Verificar cédulas que están en clientes pero no en monitoreo
SELECT 
    c.cedula,
    c.nombres,
    c.estado as estado_cliente,
    c.activo as activo_cliente,
    'Falta en monitoreo' as observacion
FROM clientes c
WHERE NOT EXISTS (
    SELECT 1 
    FROM monitoreo m 
    WHERE m.cedula = c.cedula
)
ORDER BY c.cedula;

-- 3.4. Verificar cédulas que están en monitoreo pero no en clientes
SELECT 
    m.cedula,
    m.fecha_extraccion,
    m.fecha_actualizacion,
    m.activo,
    'No existe en clientes' as observacion
FROM monitoreo m
WHERE NOT EXISTS (
    SELECT 1 
    FROM clientes c 
    WHERE c.cedula = m.cedula
)
ORDER BY m.cedula;

-- 3.5. Ver últimas cédulas agregadas
SELECT 
    cedula,
    fecha_extraccion,
    fecha_actualizacion,
    activo
FROM monitoreo
ORDER BY fecha_actualizacion DESC
LIMIT 20;

-- 3.6. Ver estadísticas por fecha
SELECT 
    DATE(fecha_extraccion) as fecha,
    COUNT(*) as cedulas_extraidas,
    COUNT(*) FILTER (WHERE activo = TRUE) as activas
FROM monitoreo
GROUP BY DATE(fecha_extraccion)
ORDER BY fecha DESC
LIMIT 30;

-- ============================================================================
-- SECCIÓN 4: FUNCIÓN PARA AUTOMATIZAR SINCRONIZACIÓN
-- ============================================================================
-- Esta sección crea una función que puede ser llamada para sincronizar

-- Crear función de sincronización
CREATE OR REPLACE FUNCTION sincronizar_monitoreo() 
RETURNS TABLE (
    nuevas_cedulas INTEGER,
    actualizadas INTEGER,
    total_registros INTEGER
) AS $$
DECLARE
    nuevas_count INTEGER;
    actualizadas_count INTEGER;
    total_count INTEGER;
BEGIN
    -- Insertar nuevas cédulas
    INSERT INTO monitoreo (cedula, fecha_extraccion, fecha_actualizacion, activo)
    SELECT 
        c.cedula,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP,
        CASE 
            WHEN c.activo = TRUE AND c.estado = 'ACTIVO' THEN TRUE
            ELSE FALSE
        END
    FROM clientes c
    WHERE NOT EXISTS (
        SELECT 1 
        FROM monitoreo m 
        WHERE m.cedula = c.cedula
    )
    ON CONFLICT (cedula) DO NOTHING;
    
    GET DIAGNOSTICS nuevas_count = ROW_COUNT;
    
    -- Actualizar existentes
    UPDATE monitoreo m
    SET 
        fecha_actualizacion = CURRENT_TIMESTAMP,
        activo = CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM clientes c 
                WHERE c.cedula = m.cedula 
                AND c.activo = TRUE 
                AND c.estado = 'ACTIVO'
            ) THEN TRUE
            ELSE FALSE
        END
    WHERE EXISTS (
        SELECT 1 
        FROM clientes c 
        WHERE c.cedula = m.cedula
    );
    
    GET DIAGNOSTICS actualizadas_count = ROW_COUNT;
    
    -- Contar total
    SELECT COUNT(*) INTO total_count FROM monitoreo;
    
    RETURN QUERY SELECT nuevas_count, actualizadas_count, total_count;
END;
$$ LANGUAGE plpgsql;

-- Ejecutar la función de sincronización
SELECT * FROM sincronizar_monitoreo();

-- ============================================================================
-- SECCIÓN 5: TRIGGER AUTOMÁTICO (OPCIONAL)
-- ============================================================================
-- Esta sección crea un trigger que actualiza automáticamente Monitoreo
-- cuando se inserta o actualiza un cliente
-- Descomenta si quieres sincronización automática

-- Crear función trigger
/*
CREATE OR REPLACE FUNCTION trigger_sincronizar_monitoreo()
RETURNS TRIGGER AS $$
BEGIN
    -- Insertar o actualizar en monitoreo cuando se inserta un cliente
    IF TG_OP = 'INSERT' THEN
        INSERT INTO monitoreo (cedula, fecha_extraccion, fecha_actualizacion, activo)
        VALUES (
            NEW.cedula,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP,
            CASE 
                WHEN NEW.activo = TRUE AND NEW.estado = 'ACTIVO' THEN TRUE
                ELSE FALSE
            END
        )
        ON CONFLICT (cedula) DO UPDATE
        SET 
            fecha_actualizacion = CURRENT_TIMESTAMP,
            activo = CASE 
                WHEN NEW.activo = TRUE AND NEW.estado = 'ACTIVO' THEN TRUE
                ELSE FALSE
            END;
        RETURN NEW;
    END IF;
    
    -- Actualizar en monitoreo cuando se actualiza un cliente
    IF TG_OP = 'UPDATE' THEN
        UPDATE monitoreo
        SET 
            fecha_actualizacion = CURRENT_TIMESTAMP,
            activo = CASE 
                WHEN NEW.activo = TRUE AND NEW.estado = 'ACTIVO' THEN TRUE
                ELSE FALSE
            END
        WHERE cedula = NEW.cedula;
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger en tabla clientes
CREATE TRIGGER trigger_monitoreo_clientes
AFTER INSERT OR UPDATE ON clientes
FOR EACH ROW
EXECUTE FUNCTION trigger_sincronizar_monitoreo();
*/

-- ============================================================================
-- SECCIÓN 6: QUERIES ÚTILES ADICIONALES
-- ============================================================================

-- 6.1. Ver todas las cédulas en monitoreo con detalles
SELECT 
    m.id,
    m.cedula,
    c.nombres as nombre_cliente,
    c.estado as estado_cliente,
    c.activo as activo_cliente,
    m.activo as activo_monitoreo,
    m.fecha_extraccion,
    m.fecha_actualizacion,
    m.observaciones
FROM monitoreo m
LEFT JOIN clientes c ON m.cedula = c.cedula
ORDER BY m.fecha_actualizacion DESC;

-- 6.2. Limpiar cédulas duplicadas (si existen)
-- Descomenta solo si necesitas limpiar duplicados
/*
DELETE FROM monitoreo
WHERE id NOT IN (
    SELECT MIN(id)
    FROM monitoreo
    GROUP BY cedula
);
*/

-- 6.3. Vaciar tabla monitoreo (CUIDADO: borra todos los datos)
-- Descomenta solo si quieres vaciar la tabla
/*
TRUNCATE TABLE monitoreo RESTART IDENTITY CASCADE;
*/

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- 
-- RESUMEN:
-- 1. Sección 1: Crea la tabla Monitoreo
-- 2. Sección 2: Sincroniza datos manualmente
-- 3. Sección 3: Queries de verificación
-- 4. Sección 4: Función para automatizar sincronización
-- 5. Sección 5: Trigger automático (opcional)
-- 6. Sección 6: Queries útiles adicionales
--
-- Para usar:
-- - Ejecutar Sección 1 una vez para crear la tabla
-- - Ejecutar Sección 2 o llamar sincronizar_monitoreo() cada vez que quieras actualizar
-- - Usar Sección 3 para verificar datos
-- - Opcionalmente activar Sección 5 para sincronización automática

