-- =============================================================================
-- Tabla variables_notificacion (variables personalizadas para plantillas)
-- Columnas: id, nombre_variable, tabla, campo_bd, descripcion, activa, fecha_creacion, fecha_actualizacion
-- =============================================================================

CREATE TABLE IF NOT EXISTS variables_notificacion (
    id SERIAL PRIMARY KEY,
    nombre_variable VARCHAR(80) NOT NULL UNIQUE,
    tabla VARCHAR(80) NOT NULL,
    campo_bd VARCHAR(120) NOT NULL,
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT true,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_variables_notificacion_nombre_variable ON variables_notificacion(nombre_variable);
CREATE INDEX IF NOT EXISTS ix_variables_notificacion_activa ON variables_notificacion(activa);

COMMENT ON TABLE variables_notificacion IS 'Variables personalizadas para plantillas de notificación ({{nombre_variable}})';

-- Verificar columnas (solo consulta, no modifica):
-- SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
--   FROM information_schema.columns
--   WHERE table_name = 'variables_notificacion'
--   ORDER BY ordinal_position;
