-- Amplía longitud de correos en clientes (+50 caracteres: 100 -> 150).
-- Alineado con frontend CLIENTE_EMAIL_MAX_LENGTH / modelos SQLAlchemy.
-- PostgreSQL. Ejecutar una vez (psql, DBeaver, etc.).

ALTER TABLE public.clientes
  ALTER COLUMN email TYPE VARCHAR(150),
  ALTER COLUMN email_secundario TYPE VARCHAR(150);

ALTER TABLE public.clientes_con_errores
  ALTER COLUMN email TYPE VARCHAR(150);
