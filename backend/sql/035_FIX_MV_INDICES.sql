-- Fix: Crear índices únicos para permitir REFRESH MATERIALIZED VIEW CONCURRENTLY
-- PostgreSQL: Para usar REFRESH MATERIALIZED VIEW CONCURRENTLY es necesario tener un índice único
-- sin cláusula WHERE sobre la vista materializada.

-- 1. Crear índice único en clientes_retrasados_mv
-- El índice es sobre el campo id (cliente_id) que es PK lógica en la vista
CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_retrasados_mv_id 
  ON clientes_retrasados_mv (id);

-- 2. Crear índice único en pagos_kpis_mv  
-- Similar, el snapshot_date es la PK lógica para mantener unicidad por fecha
CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_kpis_mv_fecha
  ON pagos_kpis_mv (fecha_snapshot);

-- Verificar que los índices se crearon correctamente
SELECT 
  schemaname,
  matviewname,
  indexname,
  indexdef
FROM pg_indexes
WHERE matviewname IN ('clientes_retrasados_mv', 'pagos_kpis_mv')
ORDER BY matviewname, indexname;
