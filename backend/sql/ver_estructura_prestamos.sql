-- =============================================================================
-- Solo CONSULTA: ver la estructura real de la tabla prestamos en tu BD.
-- No crea ni altera nada. Ejecutar en psql o en el panel de tu hosting (Render, etc.).
-- =============================================================================

-- 1) Columnas que tiene hoy la tabla prestamos (ordenadas por posición)
SELECT
    a.attname AS columna,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS tipo,
    a.attnotnull AS no_nulo,
    COALESCE(pg_catalog.pg_get_expr(d.adbin, d.adrelid), '') AS default_val
FROM pg_catalog.pg_attribute a
LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
WHERE a.attrelid = 'public.prestamos'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;

-- 2) Mismo dato vía information_schema (más portable)
SELECT
    column_name AS columna,
    data_type AS tipo,
    is_nullable AS nullable,
    column_default AS default_val
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'prestamos'
ORDER BY ordinal_position;

-- 3) Una fila de ejemplo (para ver qué columnas devuelve la BD)
SELECT * FROM prestamos LIMIT 1;
