-- Migración: añadir modalidad_pago y numero_cuotas a prestamos (para listado y formularios).
-- SOLO si tu tabla prestamos NO tiene ya estas columnas (ver con ver_estructura_prestamos.sql).
-- En la BD real confirmada, estas columnas YA EXISTEN; no ejecutar en ese caso. Idempotente.

ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS modalidad_pago VARCHAR(50);
ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS numero_cuotas INTEGER;
