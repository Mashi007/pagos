-- =============================================================================
-- 041: Columnas canónicas en `pagos` para antiduplicado Cobros sin escanear
--      toda la tabla en memoria (consultas IN acotadas por lote).
--
-- Ejecutar en PostgreSQL (producción / staging). Orden recomendado:
--   1) Esta migración (ALTER + índices en transacción, o CONCURRENTLY fuera).
--   2) python scripts/backfill_pagos_doc_canon.py  (desde la raíz del repo)
-- =============================================================================

-- Columnas (nullable hasta completar backfill; la app rellena en insert/update)
ALTER TABLE pagos
  ADD COLUMN IF NOT EXISTS doc_canon_numero TEXT,
  ADD COLUMN IF NOT EXISTS doc_canon_referencia TEXT;

COMMENT ON COLUMN pagos.doc_canon_numero IS
  'normalize_documento(numero_documento); Cobros duplicados vs pagos por IN indexado.';
COMMENT ON COLUMN pagos.doc_canon_referencia IS
  'normalize_documento(referencia_pago); Cobros duplicados vs pagos por IN indexado.';

-- Índices B-tree (rápidos para WHERE col IN (...)).
-- Si la tabla es grande en producción, sustituir por CREATE INDEX CONCURRENTLY
-- ejecutado FUERA de una transacción (psql -c "CREATE INDEX CONCURRENTLY ...").
CREATE INDEX IF NOT EXISTS ix_pagos_doc_canon_numero
  ON pagos (doc_canon_numero)
  WHERE doc_canon_numero IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_pagos_doc_canon_referencia
  ON pagos (doc_canon_referencia)
  WHERE doc_canon_referencia IS NOT NULL;
