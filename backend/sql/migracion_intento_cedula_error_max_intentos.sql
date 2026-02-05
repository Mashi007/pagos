-- Migración: intento_cedula para máx 3 intentos en ESPERANDO_CEDULA; estado 'error_max_intentos'.
-- Ejecutar cuando se use la humanización INICIO/ESPERANDO_CEDULA con límite de intentos.

ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS intento_cedula INTEGER NOT NULL DEFAULT 0;

-- El estado 'error_max_intentos' es un valor de la columna estado (VARCHAR), no requiere nueva columna.
