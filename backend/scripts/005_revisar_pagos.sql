-- Tabla temporal de validación: pagos exportados a Excel para revisión
-- No interfiere con procesos ni reglas de negocio.
-- Cuando el usuario descarga Excel de "Revisar Pagos" y guarda el archivo,
-- esos pagos se registran aquí y dejan de mostrarse en la vista Revisar Pagos.
--
-- Ejecutar: psql $DATABASE_URL -f scripts/005_revisar_pagos.sql

CREATE TABLE IF NOT EXISTS revisar_pagos (
  id SERIAL PRIMARY KEY,
  pago_id INTEGER NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
  fecha_exportacion TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(pago_id)
);

CREATE INDEX IF NOT EXISTS idx_revisar_pagos_pago_id ON revisar_pagos(pago_id);

COMMENT ON TABLE revisar_pagos IS 'Pagos exportados a Excel para revisión; excluidos de la vista Revisar Pagos. Tabla temporal de validación.';
