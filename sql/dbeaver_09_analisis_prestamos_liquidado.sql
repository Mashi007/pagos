-- =============================================================================
-- Análisis: Préstamos con estado LIQUIDADO
-- =============================================================================

-- 1) Resumen LIQUIDADO
SELECT
  COUNT(*) AS total_liquidados,
  SUM(total_financiamiento)::numeric(14,2) AS capital_total,
  SUM(numero_cuotas) AS cuotas_totales,
  COUNT(DISTINCT prestamo_id) FILTER (
    SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = prestamos.id AND c.total_pagado > 0
  ) AS con_pagos_aplicados
FROM prestamos
WHERE estado = 'LIQUIDADO';

-- 2) Detalle por préstamo LIQUIDADO
SELECT
  id,
  cliente_id,
  numero_cuotas,
  total_financiamiento::numeric(14,2),
  COALESCE(monto_pagado, 0)::numeric(14,2) AS monto_pagado_campo,
  (SELECT COALESCE(SUM(total_pagado), 0)::numeric(14,2)
   FROM cuotas c WHERE c.prestamo_id = prestamos.id) AS total_pagado_cuotas,
  fecha_aprobacion,
  fecha_creacion,
  modalidad_pago
FROM prestamos
WHERE estado = 'LIQUIDADO'
ORDER BY id;

-- 3) Cuotas de préstamos LIQUIDADO: coverage
WITH liquidado AS (
  SELECT id, numero_cuotas
  FROM prestamos
  WHERE estado = 'LIQUIDADO'
)
SELECT
  l.id AS prestamo_id,
  l.numero_cuotas AS n_declarado,
  COUNT(c.id) AS n_en_tabla,
  COUNT(c.id) FILTER (WHERE c.total_pagado > 0) AS n_pagadas,
  COALESCE(SUM(c.total_pagado), 0)::numeric(14,2) AS total_pagado
FROM liquidado l
LEFT JOIN cuotas c ON c.prestamo_id = l.id
GROUP BY l.id, l.numero_cuotas
ORDER BY l.id;

-- 4) Análisis: ¿Por qué están marcados como LIQUIDADO?
-- (Hipótesis: fueron cerrados manualmente o tienen condicion especial)
SELECT
  COUNT(*) FILTER (WHERE numero_cuotas IS NULL OR numero_cuotas = 0) AS sin_cuotas_definidas,
  COUNT(*) FILTER (WHERE monto_pagado IS NULL) AS sin_monto_pagado_registrado,
  COUNT(*) FILTER (WHERE fecha_aprobacion IS NULL) AS sin_fecha_aprobacion,
  COUNT(*) FILTER (WHERE estado IS NOT NULL AND estado <> 'LIQUIDADO') AS con_estado_diferente,
  COUNT(*) AS total_liquidados
FROM prestamos
WHERE estado = 'LIQUIDADO';

-- 5) Cuotas de LIQUIDADO: desalineaciones en cuota 1
WITH p AS (
  SELECT pr.id, pr.modalidad_pago, pr.fecha_aprobacion::date,
         c.fecha_vencimiento
  FROM prestamos pr
  JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
  WHERE pr.estado = 'LIQUIDADO'
    AND pr.fecha_aprobacion IS NOT NULL
    AND pr.numero_cuotas >= 1
)
SELECT
  p.id AS prestamo_id,
  p.modalidad_pago,
  p.fecha_aprobacion,
  p.fecha_vencimiento,
  'Desalineado cuota 1' AS observacion
FROM p
WHERE p.fecha_vencimiento::date <> (
  CASE
    WHEN UPPER(COALESCE(TRIM(p.modalidad_pago), 'MENSUAL')) = 'MENSUAL'
      THEN (p.fecha_aprobacion + INTERVAL '1 month')::date
    WHEN UPPER(COALESCE(TRIM(p.modalidad_pago), 'MENSUAL')) = 'QUINCENAL'
      THEN (p.fecha_aprobacion + INTERVAL '14 days')::date
    WHEN UPPER(COALESCE(TRIM(p.modalidad_pago), 'MENSUAL')) = 'SEMANAL'
      THEN (p.fecha_aprobacion + INTERVAL '6 days')::date
    ELSE (p.fecha_aprobacion + INTERVAL '1 month')::date
  END
)
ORDER BY prestamo_id;

-- 6) Recomendaciones
-- ¿Estos préstamos están realmente liquidados o debería revertirse su estado?
-- Calcular: cuotas pagadas / cuotas totales
WITH liquidado_progress AS (
  SELECT
    p.id,
    p.numero_cuotas,
    COUNT(c.id) FILTER (WHERE COALESCE(c.total_pagado, 0) >= c.monto_cuota - 0.01) AS n_pagadas,
    COALESCE(SUM(c.total_pagado), 0)::numeric(14,2) AS total_pagado,
    p.total_financiamiento::numeric(14,2) AS capital
  FROM prestamos p
  LEFT JOIN cuotas c ON c.prestamo_id = p.id
  WHERE p.estado = 'LIQUIDADO'
  GROUP BY p.id, p.numero_cuotas, p.total_financiamiento
)
SELECT
  id,
  numero_cuotas,
  n_pagadas,
  ROUND((n_pagadas::numeric / NULLIF(numero_cuotas, 0)) * 100, 1) AS porcentaje_pagado,
  total_pagado,
  capital,
  ROUND(total_pagado / NULLIF(capital, 0) * 100, 1) AS porcentaje_pagado_capital,
  CASE
    WHEN n_pagadas = numero_cuotas AND total_pagado >= capital - 1 THEN 'OK: Completamente pagado'
    WHEN n_pagadas < numero_cuotas AND total_pagado < capital THEN 'REVISAR: Pagos parciales'
    WHEN total_pagado = 0 THEN 'ALERTA: Sin pagos registrados'
    ELSE 'REVISAR'
  END AS recomendacion
FROM liquidado_progress
ORDER BY porcentaje_pagado_capital DESC;
