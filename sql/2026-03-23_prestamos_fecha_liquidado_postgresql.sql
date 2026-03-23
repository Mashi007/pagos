-- Alinear public.prestamos con backend/app/models/prestamo.py (fecha_liquidado).
-- Corrige: psycopg2.errors.UndefinedColumn column prestamos.fecha_liquidado does not exist
-- Ejecutar en la misma base que usa DATABASE_URL (p. ej. DBeaver / psql en Render).

ALTER TABLE prestamos ADD COLUMN IF NOT EXISTS fecha_liquidado DATE NULL;

CREATE INDEX IF NOT EXISTS ix_prestamos_fecha_liquidado ON prestamos (fecha_liquidado);

