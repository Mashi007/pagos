-- =============================================================================
-- Detalle completo por cédula / documento (PostgreSQL)
-- Documento de ejemplo: V18786296  →  cambia @doc_num y @doc_con_v abajo
--
-- Estrategia: localizar préstamos cuyo registro (to_jsonb) contenga el texto
-- del documento en algún campo. Si tu cédula NO está en prestamos sino solo en
-- otra tabla (clientes, personas, etc.), ejecuta primero la sección DISCOVERY.
-- =============================================================================

-- Parámetros (edita solo estos dos valores)
-- -----------------------------------------------------------------------------
\set doc_num '18786296'
\set doc_con_v 'V18786296'
-- Si usas DBeaver/pgAdmin y no soportas \set, reemplaza manualmente en la CTE.

-- =============================================================================
-- DISCOVERY (ejecutar si la consulta principal no devuelve filas)
-- =============================================================================
-- Columnas de prestamos:
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'prestamos'
-- ORDER BY ordinal_position;
--
-- FKs desde prestamos (titular / cliente):
-- SELECT tc.constraint_name, kcu.column_name,
--        ccu.table_schema AS fk_schema, ccu.table_name AS fk_table, ccu.column_name AS fk_column
-- FROM information_schema.table_constraints tc
-- JOIN information_schema.key_column_usage kcu
--   ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
-- JOIN information_schema.constraint_column_usage ccu
--   ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
-- WHERE tc.constraint_type = 'FOREIGN KEY'
--   AND tc.table_schema = 'public' AND tc.table_name = 'prestamos';

-- =============================================================================
-- 0) IDs de préstamo que coinciden con el documento (cualquier columna en JSON)
-- =============================================================================
-- Sustituye '18786296' y 'V18786296' si no usas psql \set
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT * FROM prestamos_match;

-- =============================================================================
-- 1) Fila completa del(los) préstamo(s)
-- =============================================================================
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT pr.*
FROM prestamos pr
JOIN prestamos_match m ON m.prestamo_id = pr.id
ORDER BY pr.id;

-- =============================================================================
-- 2) Cuotas de esos préstamos
-- =============================================================================
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT c.*
FROM cuotas c
JOIN prestamos_match m ON m.prestamo_id = c.prestamo_id
ORDER BY c.prestamo_id, c.numero_cuota;

-- =============================================================================
-- 3) Pagos de esos préstamos
-- =============================================================================
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT p.*
FROM pagos p
JOIN prestamos_match m ON m.prestamo_id = p.prestamo_id
ORDER BY p.prestamo_id, p.fecha_pago NULLS LAST, p.id;

-- =============================================================================
-- 4) Trazabilidad: pago → cuota_pagos → cuota (todo en una vista plana)
-- =============================================================================
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT
    p.id              AS pago_id,
    p.prestamo_id,
    p.fecha_pago,
    p.monto_pagado,
    cp.id             AS cuota_pago_id,
    cp.orden_aplicacion,
    cp.monto_aplicado,
    cp.es_pago_completo,
    cp.fecha_aplicacion,
    c.id              AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado    AS total_pagado_cuota
FROM prestamos_match m
JOIN pagos p ON p.prestamo_id = m.prestamo_id
LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
LEFT JOIN cuotas c ON c.id = cp.cuota_id
ORDER BY p.prestamo_id, p.id, cp.orden_aplicacion NULLS LAST;

-- =============================================================================
-- 5) Resumen por préstamo (totales)
-- =============================================================================
WITH params AS (
    SELECT '18786296'::text AS doc_num, 'V18786296'::text AS doc_con_v
),
prestamos_match AS (
    SELECT DISTINCT pr.id AS prestamo_id
    FROM prestamos pr
    CROSS JOIN params p
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_each_text(to_jsonb(pr)) AS e(k, v)
        WHERE v IS NOT NULL
          AND (
                lower(v) LIKE '%' || lower(p.doc_num) || '%'
             OR lower(v) LIKE '%' || lower(p.doc_con_v) || '%'
          )
    )
)
SELECT
    m.prestamo_id,
    COUNT(DISTINCT c.id)   AS num_cuotas,
    COUNT(DISTINCT p.id)   AS num_pagos,
    COALESCE(SUM(DISTINCT p.monto_pagado), 0) AS suma_montos_pago_distinct,  -- ojo: DISTINCT puede no ser lo ideal si un pago se cuenta mal
    SUM(p.monto_pagado)    AS suma_montos_pago
FROM prestamos_match m
LEFT JOIN cuotas c ON c.prestamo_id = m.prestamo_id
LEFT JOIN pagos p ON p.prestamo_id = m.prestamo_id
GROUP BY m.prestamo_id
ORDER BY m.prestamo_id;
