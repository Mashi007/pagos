-- Añadir columna valor_encriptado a configuracion (para datos sensibles encriptados con Fernet).
-- El modelo Configuracion ya la define; la tabla en BD no la tenía.
--
-- Ejecutar: psql $DATABASE_URL -f backend/scripts/007_add_valor_encriptado_configuracion.sql

ALTER TABLE configuracion
ADD COLUMN IF NOT EXISTS valor_encriptado BYTEA;

COMMENT ON COLUMN configuracion.valor_encriptado IS 'Valor encriptado con Fernet (API keys, contraseñas). Si existe, se prefiere sobre valor.';
