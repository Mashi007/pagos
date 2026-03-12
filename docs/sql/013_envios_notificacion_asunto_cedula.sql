-- Añadir columna asunto e índice por cedula (historial / consulta por cédula)
-- Tabla: envios_notificacion
-- Nota: ADD COLUMN IF NOT EXISTS no existe en PostgreSQL; usar el bloque DO para evitar error si ya existe.

-- PostgreSQL: añadir asunto solo si no existe
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'envios_notificacion'
      AND column_name = 'asunto'
  ) THEN
    ALTER TABLE envios_notificacion
      ADD COLUMN asunto VARCHAR(500) NULL;
  END IF;
END $$;

-- Índice por cedula (consultas de historial por cédula)
CREATE INDEX IF NOT EXISTS ix_envios_notificacion_cedula
  ON envios_notificacion (cedula);
