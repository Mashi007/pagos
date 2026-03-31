-- Migración: Crear tabla registro_cambios para auditoría de cambios
-- Propósito: Registrar todos los cambios realizados en el sistema con trazabilidad de usuario, fecha y descripción
-- Tabla: registro_cambios

CREATE TABLE IF NOT EXISTS registro_cambios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    usuario_email VARCHAR(255),
    modulo VARCHAR(100) NOT NULL,
    tipo_cambio VARCHAR(50) NOT NULL,
    descripcion TEXT NOT NULL,
    registro_id INTEGER,
    tabla_afectada VARCHAR(100),
    campos_anteriores JSONB,
    campos_nuevos JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    fecha_hora TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    vigente BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Índices para búsquedas y reportes
    CONSTRAINT registro_cambios_usuario_id_idx 
        CHECK (usuario_id > 0)
);

-- Índices para optimizar búsquedas comunes
CREATE INDEX idx_registro_cambios_usuario_id ON registro_cambios(usuario_id);
CREATE INDEX idx_registro_cambios_modulo ON registro_cambios(modulo);
CREATE INDEX idx_registro_cambios_tipo_cambio ON registro_cambios(tipo_cambio);
CREATE INDEX idx_registro_cambios_registro_id ON registro_cambios(registro_id);
CREATE INDEX idx_registro_cambios_fecha_hora ON registro_cambios(fecha_hora DESC);
CREATE INDEX idx_registro_cambios_modulo_fecha ON registro_cambios(modulo, fecha_hora DESC);
CREATE INDEX idx_registro_cambios_usuario_fecha ON registro_cambios(usuario_id, fecha_hora DESC);
CREATE INDEX idx_registro_cambios_vigente ON registro_cambios(vigente);

-- Comentarios sobre la tabla
COMMENT ON TABLE registro_cambios IS 'Tabla de auditoría: registro de todos los cambios realizados en el sistema con trazabilidad completa';
COMMENT ON COLUMN registro_cambios.usuario_id IS 'ID del usuario que realiza el cambio';
COMMENT ON COLUMN registro_cambios.usuario_email IS 'Email del usuario (desnormalizado para reportes)';
COMMENT ON COLUMN registro_cambios.modulo IS 'Módulo del sistema afectado (Préstamos, Pagos, Auditoría, etc.)';
COMMENT ON COLUMN registro_cambios.tipo_cambio IS 'Tipo de cambio: CREAR, ACTUALIZAR, ELIMINAR, EXPORTAR, etc.';
COMMENT ON COLUMN registro_cambios.descripcion IS 'Descripción legible del cambio realizado';
COMMENT ON COLUMN registro_cambios.registro_id IS 'ID del registro específico afectado';
COMMENT ON COLUMN registro_cambios.tabla_afectada IS 'Nombre de la tabla de base de datos afectada';
COMMENT ON COLUMN registro_cambios.campos_anteriores IS 'Valores anteriores de los campos modificados (JSON)';
COMMENT ON COLUMN registro_cambios.campos_nuevos IS 'Valores nuevos de los campos modificados (JSON)';
COMMENT ON COLUMN registro_cambios.fecha_hora IS 'Fecha y hora exacta del cambio (con timezone)';
