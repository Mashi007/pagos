-- Migración: columna humano en pagos_informes.
-- Regla: cuando más del 80% del texto detectado por OCR es de baja confianza (manuscrito/ilegible),
-- se marca HUMANO para indicar revisión humana y NO se inventan datos (evitar errores).
-- Ejecutar en la BD si la tabla pagos_informes ya existe.

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS humano VARCHAR(20);
