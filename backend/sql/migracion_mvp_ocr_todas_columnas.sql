-- Migración MVP OCR: añade todas las columnas que podrían faltar para que el flujo
-- (WhatsApp → foto → Drive → OCR → pagos_informes → Sheets) funcione sin errores.
-- Ejecutar en la BD de producción una vez. Todas las sentencias son idempotentes (IF NOT EXISTS).
-- Si las tablas pagos_whatsapp, conversacion_cobranza o pagos_informes no existen, ejecutar antes
-- backend/sql/migracion_pagos_whatsapp_link_imagen.sql.

-- 1) pagos_whatsapp: link de imagen (Google Drive)
ALTER TABLE pagos_whatsapp ADD COLUMN IF NOT EXISTS link_imagen TEXT;

-- 2) conversacion_cobranza: confirmación de identidad
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(100);
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS intento_confirmacion INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversacion_cobranza ADD COLUMN IF NOT EXISTS observacion TEXT;

-- 3) pagos_informes: columnas del modelo PagosInforme (OCR + informe)
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS nombre_banco VARCHAR(255);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(100);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS humano VARCHAR(20);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS observacion TEXT;
