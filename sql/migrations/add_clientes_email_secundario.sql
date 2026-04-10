-- Segundo correo opcional por cliente (máx. 2 direcciones distintas: email + email_secundario).
-- Ejecutar en la BD de producción/staging cuando despliegues el backend que usa esta columna.

ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS email_secundario VARCHAR(100) NULL;

COMMENT ON COLUMN clientes.email_secundario IS 'Correo adicional opcional; debe ser distinto de email (normalizado en aplicación).';
