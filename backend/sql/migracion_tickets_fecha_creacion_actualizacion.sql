-- Migración: añadir fecha_creacion y fecha_actualizacion a tickets
-- La tabla tickets en producción fue creada sin estas columnas; el modelo SQLAlchemy las requiere.
-- Ejecutar en la BD de Render/PostgreSQL.

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
