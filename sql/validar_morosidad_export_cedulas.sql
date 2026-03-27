-- Validacion aproximada (CASE en SQL). El Excel en la API usa clasificar_estado_cuota() en Python
-- (paridad con amortizacion); si difiere, confiar en el export o en GET .../auditoria/mora-por-cliente.
-- Mismo objetivo que el reporte de morosidad (Excel por cedula):
--   GET /api/v1/reportes/exportar/morosidad-cedulas
--   GET /api/v1/reportes/morosidad/clientes
--   GET /api/v1/reportes/morosidad/auditoria/mora-por-cliente?cedula=
-- (mora-por-prestamo es solo diagnostico por un prestamo)
-- UNICAMENTE estado calculado = 'MORA' (VENCIDO excluido). Alias c en cuotas.
-- CASE alineado con amortizacion: usa c.total_pagado (no solo SUM cuota_pagos).
-- Resultado: una fila por cedula (GROUP BY cliente_id): suma todas las cuotas MORA de todos los prestamos del cliente.

WITH por_cuota AS (
  SELECT
    cl.id AS cliente_id,
    cl.cedula,
    p.modalidad_pago,
    c.id AS cuota_id,
    c.monto_cuota,
    TRIM(BOTH FROM (
CASE
  WHEN COALESCE(c.total_pagado, 0)::numeric >= COALESCE(c.monto_cuota, 0)::numeric - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE(c.total_pagado, 0)::numeric > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date >= (c.fecha_vencimiento::date + INTERVAL '4 months' + INTERVAL '1 day')::date THEN 'MORA'
      ELSE 'VENCIDO'
    END
END
    )) AS estado_calc
  FROM cuotas c
  JOIN prestamos p ON c.prestamo_id = p.id
  JOIN clientes cl ON p.cliente_id = cl.id
  WHERE cl.estado = 'ACTIVO'
    AND p.estado = 'APROBADO'
),
filtrado AS (
  SELECT *
  FROM por_cuota
  WHERE estado_calc = 'MORA'
)
SELECT
  cedula,
  string_agg(DISTINCT modalidad_pago, ', ' ORDER BY modalidad_pago) AS modalidad,
  COUNT(cuota_id) AS cantidad_cuotas,
  COALESCE(SUM(monto_cuota), 0) AS total_usd
FROM filtrado
GROUP BY cliente_id, cedula
ORDER BY cedula;
