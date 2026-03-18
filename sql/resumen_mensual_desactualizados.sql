-- Resumen: cuantos prestamos MENSUAL tienen cuotas con vencimiento
-- que NO siguen la regla "mismo dia cada mes".
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    COALESCE((p.fecha_aprobacion)::date, p.fecha_base_calculo) AS fecha_base
  FROM prestamos p
  WHERE UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
    AND (p.fecha_aprobacion IS NOT NULL OR p.fecha_base_calculo IS NOT NULL)
),
expected AS (
  SELECT
    b.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
),
desactualizados AS (
  SELECT DISTINCT prestamo_id
  FROM expected
  WHERE actual_vencimiento <> esperado_vencimiento
)
SELECT
  (SELECT COUNT(*) FROM prestamos WHERE UPPER(TRIM(COALESCE(modalidad_pago, ''))) = 'MENSUAL') AS total_prestamos_mensual,
  (SELECT COUNT(*) FROM desactualizados) AS prestamos_con_cuotas_desactualizadas;
