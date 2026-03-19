-- =============================================================================
-- Verificación: fechas de amortización según frecuencia de pago
-- Reglas de negocio:
--   QUINCENAL: fin de cada quincena; cuota n = aprobacion + (15*n - 1) días.
--     Ejemplo: 1 ene → 15 ene (cuota 1), 30 ene (cuota 2), 14 feb (cuota 3), 1 mar, ...
--   MENSUAL: mismo día del mes que la fecha_aprobacion.
--     Cuota 1 = aprobacion + 1 mes, Cuota 2 = +2 meses, ...
--     Ejemplo: 2 ene → 2 feb, 2 mar, 2 abr, ...
-- =============================================================================

-- 1) Resumen por modalidad: total préstamos y cuántos tienen al menos una cuota con vencimiento incorrecto
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) AS modalidad,
    (p.fecha_aprobacion)::date AS fecha_base
  FROM prestamos p
  WHERE p.fecha_aprobacion IS NOT NULL
    AND UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) IN ('MENSUAL', 'QUINCENAL')
),
expected AS (
  SELECT
    b.prestamo_id,
    b.modalidad,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    CASE
      WHEN b.modalidad = 'MENSUAL' THEN (b.fecha_base + (c.numero_cuota || ' months')::interval)::date
      WHEN b.modalidad = 'QUINCENAL' THEN (b.fecha_base + (15 * c.numero_cuota - 1) * interval '1 day')::date
      ELSE NULL
    END AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
),
errores AS (
  SELECT prestamo_id, modalidad, numero_cuota, actual_vencimiento, esperado_vencimiento
  FROM expected
  WHERE esperado_vencimiento IS NOT NULL
    AND actual_vencimiento IS DISTINCT FROM esperado_vencimiento
),
prestamos_con_error AS (
  SELECT DISTINCT prestamo_id, modalidad FROM errores
)
SELECT
  'MENSUAL' AS modalidad,
  (SELECT COUNT(*) FROM prestamos WHERE UPPER(TRIM(COALESCE(modalidad_pago, ''))) = 'MENSUAL' AND fecha_aprobacion IS NOT NULL) AS total_prestamos,
  (SELECT COUNT(*) FROM prestamos_con_error WHERE modalidad = 'MENSUAL') AS prestamos_con_cuotas_incorrectas
UNION ALL
SELECT
  'QUINCENAL',
  (SELECT COUNT(*) FROM prestamos WHERE UPPER(TRIM(COALESCE(modalidad_pago, ''))) = 'QUINCENAL' AND fecha_aprobacion IS NOT NULL),
  (SELECT COUNT(*) FROM prestamos_con_error WHERE modalidad = 'QUINCENAL');


-- 2) Detalle: cuotas con vencimiento incorrecto (actual vs esperado según regla)
--    Útil para ver la distorsión (ej. si quincenal se calculó como mensual o con 15*n-1)
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    p.modalidad_pago,
    (p.fecha_aprobacion)::date AS fecha_base
  FROM prestamos p
  WHERE p.fecha_aprobacion IS NOT NULL
    AND UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) IN ('MENSUAL', 'QUINCENAL')
),
expected AS (
  SELECT
    b.prestamo_id,
    b.modalidad_pago,
    b.fecha_base,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    CASE
      WHEN UPPER(TRIM(b.modalidad_pago)) = 'MENSUAL' THEN (b.fecha_base + (c.numero_cuota || ' months')::interval)::date
      WHEN UPPER(TRIM(b.modalidad_pago)) = 'QUINCENAL' THEN (b.fecha_base + (15 * c.numero_cuota - 1) * interval '1 day')::date
      ELSE NULL
    END AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
)
SELECT
  prestamo_id,
  modalidad_pago,
  fecha_base AS fecha_aprobacion,
  numero_cuota,
  actual_vencimiento,
  esperado_vencimiento,
  (actual_vencimiento - esperado_vencimiento) AS dias_diferencia
FROM expected
WHERE esperado_vencimiento IS NOT NULL
  AND actual_vencimiento IS DISTINCT FROM esperado_vencimiento
ORDER BY modalidad_pago, prestamo_id, numero_cuota;


-- 2b) MENSUAL: diagnóstico — si actual = último día del mes (distorsión típica "fin de mes" vs "mismo día")
WITH base AS (
  SELECT p.id AS prestamo_id, p.modalidad_pago, (p.fecha_aprobacion)::date AS fecha_base
  FROM prestamos p
  WHERE p.fecha_aprobacion IS NOT NULL
    AND UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
),
expected AS (
  SELECT
    b.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
)
SELECT
  prestamo_id,
  numero_cuota,
  actual_vencimiento,
  esperado_vencimiento,
  (actual_vencimiento - esperado_vencimiento) AS dias_diferencia,
  CASE
    WHEN actual_vencimiento = (date_trunc('month', actual_vencimiento) + interval '1 month - 1 day')::date
    THEN 'actual_es_fin_de_mes'
    ELSE 'otro'
  END AS diagnostico_mensual
FROM expected
WHERE actual_vencimiento <> esperado_vencimiento
ORDER BY prestamo_id, numero_cuota;


-- 3) QUINCENAL: diagnóstico — regla correcta = 15*n-1 (1 ene → 15 ene, 30 ene, 14 feb)
--    Lista solo cuotas donde actual <> esperado_15n_menos_1
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    (p.fecha_aprobacion)::date AS fecha_base
  FROM prestamos p
  WHERE p.fecha_aprobacion IS NOT NULL
    AND UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'QUINCENAL'
),
comparacion AS (
  SELECT
    b.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (15 * c.numero_cuota - 1) * interval '1 day')::date AS esperado_15n_menos_1
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
)
SELECT
  prestamo_id,
  numero_cuota,
  actual_vencimiento,
  esperado_15n_menos_1 AS vencimiento_esperado_quincenal,
  (actual_vencimiento - esperado_15n_menos_1) AS dias_diferencia
FROM comparacion
WHERE actual_vencimiento IS DISTINCT FROM esperado_15n_menos_1
ORDER BY prestamo_id, numero_cuota;


-- 4) MENSUAL: cuotas que no cumplen "mismo día del mes" (como en verificar_mensual_sql)
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    (p.fecha_aprobacion)::date AS fecha_base
  FROM prestamos p
  WHERE UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
    AND p.fecha_aprobacion IS NOT NULL
),
expected AS (
  SELECT
    b.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
)
SELECT
  prestamo_id,
  numero_cuota,
  actual_vencimiento,
  esperado_vencimiento,
  (actual_vencimiento - esperado_vencimiento) AS dias_diferencia
FROM expected
WHERE actual_vencimiento <> esperado_vencimiento
ORDER BY prestamo_id, numero_cuota;


-- 5) Ejemplo numérico: cómo debería verse un préstamo QUINCENAL (aprobación 1 ene)
--    Regla: 15*n-1 días. Cuota 1: 15 ene, Cuota 2: 30 ene, Cuota 3: 14 feb, Cuota 4: 1 mar, ...
SELECT
  n AS numero_cuota,
  ('2025-01-01'::date + (15 * n - 1) * interval '1 day')::date AS vencimiento_esperado_quincenal
FROM generate_series(1, 8) AS n;


-- 6) Ejemplo numérico: cómo debería verse un préstamo MENSUAL (aprobación 2 ene)
--    Cuota 1: 2 feb, Cuota 2: 2 mar, Cuota 3: 2 abr, ...
SELECT
  n AS numero_cuota,
  ('2025-01-02'::date + (n || ' months')::interval)::date AS vencimiento_esperado_mensual
FROM generate_series(1, 6) AS n;
