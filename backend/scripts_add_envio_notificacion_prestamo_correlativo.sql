-- Añade prestamo_id y correlativo a envios_notificacion para el número correlativo de cobranza (N° RAP-COB-{id}-{correlativo}).
-- Ejecutar una vez en la BD.

ALTER TABLE envios_notificacion
  ADD COLUMN IF NOT EXISTS prestamo_id INTEGER NULL,
  ADD COLUMN IF NOT EXISTS correlativo INTEGER NULL;

CREATE INDEX IF NOT EXISTS ix_envios_notificacion_prestamo_id ON envios_notificacion (prestamo_id);
