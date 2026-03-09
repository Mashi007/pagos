-- Columna A: cambiar "Correo Origen" por "Asunto". Aquí se guarda el asunto del correo.
-- Ejecutar una vez en la BD (o usar: alembic upgrade head).

ALTER TABLE pagos_gmail_sync_item
ADD COLUMN asunto VARCHAR(500) NULL;

-- Opcional: rellenar asunto con correo_origen en filas existentes (para registros ya guardados sin asunto)
-- UPDATE pagos_gmail_sync_item SET asunto = correo_origen WHERE asunto IS NULL;
