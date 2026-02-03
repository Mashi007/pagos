-- Migración: añadir modalidad_pago y numero_cuotas a prestamos (para listado y formularios).
-- Ejecutar en la BD si la tabla prestamos ya existía sin estas columnas. Idempotente.

ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS modalidad_pago VARCHAR(50);
ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS numero_cuotas INTEGER;
