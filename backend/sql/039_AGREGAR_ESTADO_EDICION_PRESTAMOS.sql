-- Migración: Agregar columna estado_edicion a tabla prestamos
-- Propósito: Rastrear si un préstamo está en edición o completado
-- Valores: EN_EDICION | COMPLETADO (default: COMPLETADO)

ALTER TABLE prestamos 
ADD COLUMN IF NOT EXISTS estado_edicion VARCHAR(50) NOT NULL DEFAULT 'COMPLETADO';

-- Crear índice para búsquedas por estado_edicion
CREATE INDEX IF NOT EXISTS idx_prestamos_estado_edicion ON prestamos(estado_edicion);

-- Comentario sobre la columna
COMMENT ON COLUMN prestamos.estado_edicion IS 'Estado del préstamo en el flujo de edición: EN_EDICION (editándose) o COMPLETADO (guardado)';
