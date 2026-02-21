-- Índices para optimizar consultas de Dashboard y Reportes
-- Ejecutar: psql $DATABASE_URL -f scripts/004_add_dashboard_indexes.sql
-- O desde DBeaver/pgAdmin: ejecutar este archivo
--
-- Para producción con tablas en uso, usar CONCURRENTLY (ejecutar cada CREATE por separado):
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_... ON tabla (col);

-- Cuotas: JOINs con prestamos + filtros por fecha_pago, fecha_vencimiento
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_pago
  ON cuotas (prestamo_id, fecha_pago);

CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_vencimiento
  ON cuotas (prestamo_id, fecha_vencimiento);

CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_pago
  ON cuotas (fecha_pago);

CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento
  ON cuotas (fecha_vencimiento);

-- Prestamos: join con clientes + filtros por estado, fecha_registro
CREATE INDEX IF NOT EXISTS idx_prestamos_cliente_estado
  ON prestamos (cliente_id, estado);

CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro
  ON prestamos (fecha_registro);

CREATE INDEX IF NOT EXISTS idx_prestamos_estado_fecha_registro
  ON prestamos (estado, fecha_registro);

-- Pagos: filtros por fecha_pago
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago
  ON pagos (fecha_pago);

CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_fecha
  ON pagos (prestamo_id, fecha_pago);
