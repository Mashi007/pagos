-- Añadir columna observaciones a pagos_con_errores.
-- Almacena solo los nombres de campos con problema, separados por coma (ej: cedula,fecha_pago).
--
-- Ejecutar: psql $DATABASE_URL -f backend/scripts/008_add_observaciones_pagos_con_errores.sql

ALTER TABLE pagos_con_errores
ADD COLUMN IF NOT EXISTS observaciones VARCHAR(255);

COMMENT ON COLUMN pagos_con_errores.observaciones IS 'Nombres de campos con problema (separados por coma). Ej: cedula,fecha_pago,numero_documento';
