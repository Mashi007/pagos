-- Migración: asegurar que conversacion_cobranza tenga todas las columnas del modelo SQLAlchemy.
-- Ejecutar en DBeaver o psql. Si la columna ya existe, no hace nada (sin mensaje "skipping").
-- Seguro ejecutar varias veces.

DO $$
BEGIN
  -- Columnas de intentos y flujo de cobranza
  ALTER TABLE conversacion_cobranza ADD COLUMN intento_cedula INTEGER NOT NULL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN intento_foto INTEGER NOT NULL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN intento_confirmacion INTEGER NOT NULL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN observacion TEXT;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN pagos_informe_id_pendiente INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN confirmacion_paso INTEGER NOT NULL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN confirmacion_esperando_valor VARCHAR(30);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE conversacion_cobranza ADD COLUMN nombre_cliente VARCHAR(100);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
