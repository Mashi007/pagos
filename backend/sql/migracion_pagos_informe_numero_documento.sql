-- Migración: columna numero_documento en pagos_informes (OCR: número de documento/recibo; formato variable; se ubica por palabras clave configurables)
-- Ejecutar en la BD si la tabla pagos_informes ya existe.

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(100);
