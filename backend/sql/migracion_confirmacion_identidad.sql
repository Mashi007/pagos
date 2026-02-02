-- Migración: confirmación de identidad (nombre_cliente, intento_confirmacion, observacion) y columna Observación en informes.
-- Ejecutar después de migracion_pagos_whatsapp_link_imagen.sql.

-- 1) conversacion_cobranza: nombre del cliente (desde tabla clientes), intentos de confirmación, observación
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(100);
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS intento_confirmacion INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS observacion TEXT;

-- 2) pagos_informes: columna observación (ej. "No confirma identidad")
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS observacion TEXT;
