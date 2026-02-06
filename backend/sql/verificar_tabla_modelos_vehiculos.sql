-- =============================================================================
-- Verificación en DBeaver: tabla modelos_vehiculos
-- Usada por: https://rapicredit.onrender.com/pagos/modelos-vehiculos
-- Ejecutar cada bloque por separado o todo junto según tu cliente.
-- =============================================================================

-- 1) ¿Existe la tabla?
SELECT EXISTS (
  SELECT 1
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name = 'modelos_vehiculos'
) AS tabla_existe;


-- 2) Estructura de la tabla (columnas, tipo, nullable, default)
SELECT
  column_name   AS columna,
  data_type     AS tipo_dato,
  character_maximum_length AS max_longitud,
  numeric_precision AS precision,
  numeric_scale AS escala,
  is_nullable   AS nullable,
  column_default AS defecto
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'modelos_vehiculos'
ORDER BY ordinal_position;


-- 3) Índices de la tabla
SELECT
  i.relname AS indice,
  a.attname AS columna,
  ix.indisunique AS es_único,
  ix.indisprimary AS es_primaria
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey) AND a.attnum > 0 AND NOT a.attisdropped
WHERE t.relkind = 'r'
  AND t.relname = 'modelos_vehiculos'
ORDER BY i.relname, a.attnum;


-- 4) Cantidad de registros
SELECT COUNT(*) AS total_registros FROM public.modelos_vehiculos;


-- 5) Datos actuales (vista de ejemplo)
SELECT
  id,
  modelo,
  activo,
  precio,
  created_at,
  updated_at
FROM public.modelos_vehiculos
ORDER BY modelo
LIMIT 100;


-- 6) Comentario de la tabla (si existe)
SELECT
  obj_description(c.oid, 'pg_class') AS comentario_tabla
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = 'modelos_vehiculos';
