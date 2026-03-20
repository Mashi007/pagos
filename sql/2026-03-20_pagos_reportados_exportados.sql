-- Crear tabla para persistir pagos reportados aprobados ya exportados a Excel
CREATE TABLE IF NOT EXISTS pagos_reportados_exportados (
  id SERIAL PRIMARY KEY,
  pago_reportado_id INTEGER NOT NULL UNIQUE,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_pagos_reportados_exportados_pago
    FOREIGN KEY (pago_reportado_id)
    REFERENCES pagos_reportados (id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_pagos_reportados_exportados_pago_reportado_id
  ON pagos_reportados_exportados (pago_reportado_id);

-- Rollback opcional
-- DROP TABLE IF EXISTS pagos_reportados_exportados;
