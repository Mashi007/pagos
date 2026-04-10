-- Agrega correo secundario a clientes (lookup pipeline Pagos Gmail: email principal, luego este).
-- Ejecutar una vez contra la BD de producción/desarrollo (psql, DBeaver, etc.).
-- PostgreSQL 9.1+

ALTER TABLE public.clientes
  ADD COLUMN IF NOT EXISTS email_secundario VARCHAR(100) NULL;
