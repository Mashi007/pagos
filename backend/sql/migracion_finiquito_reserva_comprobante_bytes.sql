-- Reserva Visto: guardar bytes del comprobante para re-OCR sin re-leer Drive/BD.
-- Ejecutar en la misma base que DATABASE_URL (prod: tras desplegar backend 073).

ALTER TABLE finiquito_conciliacion_reserva
  ADD COLUMN IF NOT EXISTS comprobante_imagen_data BYTEA NULL;

ALTER TABLE finiquito_conciliacion_reserva
  ADD COLUMN IF NOT EXISTS comprobante_content_type VARCHAR(80) NULL;

ALTER TABLE finiquito_conciliacion_reserva
  ADD COLUMN IF NOT EXISTS comprobante_nombre_archivo VARCHAR(255) NULL;
