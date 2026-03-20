-- ============================================================================
-- QUERIES OPTIMIZADAS: Verificacion de pagos (Rendimiento mejorado)
-- ============================================================================

-- 1. RESUMEN RAPIDO (< 1 segundo)
-- ============================================================================
SELECT 
  COUNT(*) AS total_pagos,
  COUNT(DISTINCT cp.pago_id) AS pagos_asignados,
  COUNT(*) - COUNT(DISTINCT cp.pago_id) AS pagos_sin_asignar,
  ROUND((COUNT(*) - COUNT(DISTINCT cp.pago_id))::numeric / COUNT(*) * 100, 2) AS porcentaje_sin_asignar,
  SUM(monto_pagado) AS suma_total_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS suma_aplicada,
  SUM(monto_pagado) - COALESCE(SUM(cp.monto_aplicado), 0) AS diferencia_no_aplicada
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id;


-- 2. CUOTAS POR ESTADO (< 1 segundo)
-- ============================================================================
SELECT 
  estado,
  COUNT(*) AS cantidad,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS porcentaje
FROM cuotas
GROUP BY estado
ORDER BY cantidad DESC;


-- 3. PRESTAMOS POR ESTADO (< 1 segundo)
-- ============================================================================
SELECT 
  estado,
  COUNT(*) AS cantidad,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS porcentaje,
  ROUND(SUM(total_financiamiento), 2) AS suma_capital
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;


-- 4. PAGOS SIN ASIGNAR - LISTADO RAPIDO (< 2 segundos)
-- ============================================================================
SELECT 
  id AS pago_id,
  fecha_pago,
  monto_pagado,
  referencia_pago,
  prestamo_id,
  estado
FROM pagos
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id)
ORDER BY fecha_pago DESC
LIMIT 100;


-- 5. ESTADISTICAS CONSOLIDADAS (< 1 segundo)
-- ============================================================================
SELECT 
  'Total Pagos' AS metrica,
  COUNT(*)::TEXT FROM pagos
UNION ALL
SELECT 'Pagos Asignados', COUNT(DISTINCT pago_id)::TEXT FROM cuota_pagos
UNION ALL
SELECT 'Total Cuotas', COUNT(*)::TEXT FROM cuotas
UNION ALL
SELECT 'Cuotas PAGADAS', COUNT(*)::TEXT FROM cuotas WHERE estado = 'PAGADO'
UNION ALL
SELECT 'Cuotas PENDIENTES', COUNT(*)::TEXT FROM cuotas WHERE estado = 'PENDIENTE'
UNION ALL
SELECT 'Prestamos APROBADO', COUNT(*)::TEXT FROM prestamos WHERE estado = 'APROBADO'
UNION ALL
SELECT 'Prestamos LIQUIDADO', COUNT(*)::TEXT FROM prestamos WHERE estado = 'LIQUIDADO';


-- 6. TASA DE CONCILIACION (< 1 segundo)
-- ============================================================================
WITH stats AS (
  SELECT 
    COUNT(DISTINCT pg.id) AS total_pagos,
    COUNT(DISTINCT cp.pago_id) AS pagos_con_cuota,
    SUM(pg.monto_pagado) AS suma_total,
    SUM(cp.monto_aplicado) AS suma_aplicada
  FROM pagos pg
  LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
)
SELECT 
  ROUND(100.0 * pagos_con_cuota / total_pagos, 2) AS tasa_conciliacion_pagos_pct,
  ROUND(100.0 * suma_aplicada / suma_total, 2) AS tasa_conciliacion_monto_pct,
  total_pagos,
  pagos_con_cuota,
  ROUND(suma_total, 2) AS suma_total,
  ROUND(suma_aplicada, 2) AS suma_aplicada
FROM stats;


-- 7. INDICES RECOMENDADOS (ejecutar una sola vez)
-- ============================================================================
-- CREATE INDEX IF NOT EXISTS idx_cuota_pagos_pago_id ON cuota_pagos(pago_id);
-- CREATE INDEX IF NOT EXISTS idx_cuota_pagos_cuota_id ON cuota_pagos(cuota_id);
-- CREATE INDEX IF NOT EXISTS idx_pagos_prestamo_id ON pagos(prestamo_id);
-- CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id ON cuotas(prestamo_id);
-- CREATE INDEX IF NOT EXISTS idx_cuotas_estado ON cuotas(estado);
-- CREATE INDEX IF NOT EXISTS idx_prestamos_estado ON prestamos(estado);
