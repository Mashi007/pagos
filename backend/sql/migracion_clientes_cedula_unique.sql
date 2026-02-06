-- =============================================================================
-- Migración: UNIQUE en clientes.cedula
-- Garantiza en BD que no pueda haber dos clientes con la misma cédula.
-- Referencia: docs/REGLAS_NEGOCIO_CLIENTES.md
-- =============================================================================

-- 1) OPCIONAL: Verificar si hay duplicados antes de aplicar. Si hay filas, hay que corregir datos primero.
-- SELECT cedula, COUNT(*) AS repeticiones, array_agg(id ORDER BY id) AS ids
-- FROM public.clientes
-- GROUP BY cedula
-- HAVING COUNT(*) > 1;

-- 2) Añadir constraint UNIQUE (falla si ya existe el constraint o si hay cédulas duplicadas)
ALTER TABLE public.clientes
  ADD CONSTRAINT uq_clientes_cedula UNIQUE (cedula);

-- Si el constraint ya existe: ERROR: relation "uq_clientes_cedula" already exists
-- Si hay duplicados: ERROR: could not create unique index "uq_clientes_cedula" / duplicate key value
-- En ese caso, ejecutar la consulta del paso 1, corregir datos y volver a ejecutar este script.
