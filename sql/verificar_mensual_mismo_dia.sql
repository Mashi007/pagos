-- Verifica que las cuotas de prestamos con modalidad_pago MENSUAL tengan
-- vencimiento el mismo dia del mes (logica: fecha_base + N meses).
-- fecha_base = fecha_aprobacion o fecha_base_calculo.

-- 1) Prestamos MENSUAL con al menos una cuota cuyo vencimiento NO coincide
--    con el esperado (mismo dia cada mes).
WITH base AS (
  SELECT
    p.id AS prestamo_id,
    p.cliente_id,
    p.modalidad_pago,
    COALESCE(
      (p.fecha_aprobacion)::date,
      p.fecha_base_calculo
    ) AS fecha_base
  FROM prestamos p
  WHERE UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
    AND (p.fecha_aprobacion IS NOT NULL OR p.fecha_base_calculo IS NOT NULL)
),
expected AS (
  SELECT
    b.prestamo_id,
    c.id AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento AS actual_vencimiento,
    (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
  FROM base b
  JOIN cuotas c ON c.prestamo_id = b.prestamo_id
)
SELECT
  prestamo_id,
  cuota_id,
  numero_cuota,
  actual_vencimiento,
  esperado_vencimiento,
  (actual_vencimiento <> esperado_vencimiento) AS desactualizado
FROM expected
WHERE actual_vencimiento <> esperado_vencimiento
ORDER BY prestamo_id, numero_cuota;
