-- =============================================================================
-- Migración: UNIQUE en pagos.numero_documento
-- Regla: Nº documento no puede repetirse (vacíos/NULL sí pueden estar repetidos).
-- =============================================================================

-- 1) OPCIONAL: Verificar si hay numero_documento duplicados antes de aplicar.
--    Si hay filas, hay que corregir datos (unificar o dejar uno, el resto NULL/vacío) y volver a ejecutar.
-- SELECT numero_documento, COUNT(*) AS repeticiones, array_agg(id ORDER BY id) AS ids
-- FROM public.pagos
-- WHERE numero_documento IS NOT NULL AND TRIM(numero_documento) <> ''
-- GROUP BY numero_documento
-- HAVING COUNT(*) > 1;

-- 2) Añadir constraint UNIQUE (falla si ya existe el constraint o si hay duplicados)
ALTER TABLE public.pagos
  ADD CONSTRAINT uq_pagos_numero_documento UNIQUE (numero_documento);

-- Si el constraint ya existe: ERROR: relation "uq_pagos_numero_documento" already exists
-- Si hay duplicados: ERROR: could not create unique index ... duplicate key value
-- En ese caso, ejecutar la consulta del paso 1, corregir datos y volver a ejecutar este script.
