-- =============================================================================
-- DBeaver: verificar regla ESTRICTA "NO DUPLICADOS" en tabla clientes
-- Campos: cédula, nombres, teléfono, email. En carga masiva se pueden guardar
-- solo los que cumplen; los duplicados quedan marcados hasta que se corrijan.
-- Ejecutar cada bloque por separado (seleccionar y F9 o Ctrl+Enter).
-- Resultado esperado: consultas de duplicados = 0 filas; constraint existe.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Constraint UNIQUE en cédula (debe existir)
-- -----------------------------------------------------------------------------
SELECT conname AS constraint_name,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.clientes'::regclass
  AND contype = 'u';

-- Debe aparecer al menos: uq_clientes_cedula UNIQUE (cedula)
-- Si no aparece, ejecutar: backend/sql/migracion_clientes_cedula_unique.sql


-- -----------------------------------------------------------------------------
-- 2) Duplicados por CÉDULA (debe devolver 0 filas)
-- -----------------------------------------------------------------------------
SELECT cedula,
       COUNT(*) AS repeticiones,
       array_agg(id ORDER BY id) AS ids_clientes
FROM public.clientes
GROUP BY cedula
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;

-- Resultado esperado: 0 filas. Si hay filas, hay duplicados y hay que corregir.


-- -----------------------------------------------------------------------------
-- 3) Duplicados por EMAIL (cuando no está vacío) (debe devolver 0 filas)
-- -----------------------------------------------------------------------------
SELECT email,
       COUNT(*) AS repeticiones,
       array_agg(id ORDER BY id) AS ids_clientes
FROM public.clientes
WHERE TRIM(COALESCE(email, '')) <> ''
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;

-- Resultado esperado: 0 filas.


-- -----------------------------------------------------------------------------
-- 4) Duplicados por NOMBRES completos (debe devolver 0 filas)
-- -----------------------------------------------------------------------------
SELECT nombres,
       COUNT(*) AS repeticiones,
       array_agg(id ORDER BY id) AS ids_clientes
FROM public.clientes
GROUP BY nombres
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;

-- Resultado esperado: 0 filas.


-- -----------------------------------------------------------------------------
-- 5) Duplicados por TELÉFONO (solo dígitos; debe devolver 0 filas)
-- -----------------------------------------------------------------------------
SELECT regexp_replace(telefono, '\D', '', 'g') AS telefono_solo_digitos,
       COUNT(*) AS repeticiones,
       array_agg(id ORDER BY id) AS ids_clientes,
       array_agg(telefono) AS telefonos_originales
FROM public.clientes
WHERE telefono IS NOT NULL
  AND LENGTH(regexp_replace(telefono, '\D', '', 'g')) >= 8
GROUP BY regexp_replace(telefono, '\D', '', 'g')
HAVING COUNT(*) > 1
ORDER BY repeticiones DESC;

-- Resultado esperado: 0 filas.


-- -----------------------------------------------------------------------------
-- 6) Resumen: total clientes y conteo de cédulas únicas (deben coincidir)
-- -----------------------------------------------------------------------------
SELECT (SELECT COUNT(*) FROM public.clientes) AS total_filas,
       (SELECT COUNT(DISTINCT cedula) FROM public.clientes) AS cedulas_unicas,
       (SELECT COUNT(*) FROM public.clientes) - (SELECT COUNT(DISTINCT cedula) FROM public.clientes) AS duplicados_cedula;

-- Resultado esperado: duplicados_cedula = 0 (total_filas = cedulas_unicas).
