-- Migración: columnas adicionales para informe de pagos (Google Sheets columnas G, H, J).
-- Ejecutar en DBeaver (o en Render) para alinear BD con hoja "Pagos_Registrados" A-J.
-- G = nombre_cliente, H = estado_conciliacion, I = fecha_informe (ya existe), J = telefono.

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS nombre_cliente VARCHAR(255);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS estado_conciliacion VARCHAR(50);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS telefono VARCHAR(30);

CREATE INDEX IF NOT EXISTS ix_pagos_informes_estado_conciliacion ON pagos_informes (estado_conciliacion);
CREATE INDEX IF NOT EXISTS ix_pagos_informes_telefono ON pagos_informes (telefono);
