-- ============================================================================
-- VERIFICACION: Todos los pagos estan cargados a cuotas respectivas
-- ============================================================================

-- 1. RESUMEN: Pagos totales vs Pagos aplicados a cuotas
-- ============================================================================
SELECT 
  COUNT(*) AS total_pagos_registrados,
  SUM(monto_pagado) AS suma_pagos_registrados,
  COUNT(DISTINCT pago_id) FILTER (WHERE pago_id IS NOT NULL) AS pagos_con_cuotas_asignadas,
  SUM(monto_aplicado) FILTER (WHERE pago_id IS NOT NULL) AS suma_pagos_aplicados,
  COUNT(*) - COUNT(DISTINCT pago_id) FILTER (WHERE pago_id IS NOT NULL) AS pagos_sin_asignar,
  SUM(monto_pagado) - COALESCE(SUM(monto_aplicado) FILTER (WHERE pago_id IS NOT NULL), 0) AS diferencia_no_aplicada
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id;


-- 2. PAGOS NO ASIGNADOS (sin cuota_pago asociada)
-- ============================================================================
SELECT 
  pg.id,
  pg.fecha_pago,
  pg.monto_pagado,
  pg.referencia_pago,
  pg.estado,
  pg.prestamo_id,
  COUNT(cp.id) AS cuotas_asignadas
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
GROUP BY pg.id, pg.fecha_pago, pg.monto_pagado, pg.referencia_pago, pg.estado, pg.prestamo_id
HAVING COUNT(cp.id) = 0
ORDER BY pg.fecha_pago DESC;


-- 3. PAGOS PARCIALMENTE APLICADOS (suma aplicada < monto pagado)
-- ============================================================================
SELECT 
  pg.id AS pago_id,
  pg.fecha_pago,
  pg.monto_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS total_aplicado,
  pg.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0) AS monto_sin_aplicar,
  ROUND(100.0 * COALESCE(SUM(cp.monto_aplicado), 0) / NULLIF(pg.monto_pagado, 0), 2) AS porcentaje_aplicado,
  COUNT(cp.id) AS cuotas_tocadas,
  pg.referencia_pago,
  pg.estado
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
GROUP BY pg.id, pg.fecha_pago, pg.monto_pagado, pg.referencia_pago, pg.estado
HAVING COALESCE(SUM(cp.monto_aplicado), 0) > 0 
   AND COALESCE(SUM(cp.monto_aplicado), 0) < pg.monto_pagado
ORDER BY pg.id;


-- 4. PAGOS COMPLETAMENTE APLICADOS (suma aplicada = monto pagado)
-- ============================================================================
SELECT 
  pg.id AS pago_id,
  pg.fecha_pago,
  pg.monto_pagado,
  SUM(cp.monto_aplicado) AS total_aplicado,
  COUNT(cp.id) AS cuotas_tocadas,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_diferentes,
  pg.referencia_pago,
  pg.estado
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
WHERE cp.id IS NOT NULL
GROUP BY pg.id, pg.fecha_pago, pg.monto_pagado, pg.referencia_pago, pg.estado
HAVING ABS(pg.monto_pagado - SUM(cp.monto_aplicado)) < 0.01
ORDER BY pg.id;


-- 5. PAGOS SOBRE-APLICADOS (suma aplicada > monto pagado)
-- ============================================================================
SELECT 
  pg.id AS pago_id,
  pg.fecha_pago,
  pg.monto_pagado,
  SUM(cp.monto_aplicado) AS total_aplicado,
  SUM(cp.monto_aplicado) - pg.monto_pagado AS exceso_aplicado,
  ROUND(100.0 * SUM(cp.monto_aplicado) / NULLIF(pg.monto_pagado, 0), 2) AS porcentaje_aplicado,
  COUNT(cp.id) AS cuotas_tocadas,
  pg.referencia_pago,
  pg.estado,
  'ERROR: PAGO SOBRE-APLICADO' AS tipo_error
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
WHERE cp.id IS NOT NULL
GROUP BY pg.id, pg.fecha_pago, pg.monto_pagado, pg.referencia_pago, pg.estado
HAVING SUM(cp.monto_aplicado) > pg.monto_pagado
ORDER BY pg.id;


-- 6. DISTRIBUCION: Estados de aplicacion por pago
-- ============================================================================
WITH aplicacion_pagos AS (
  SELECT 
    pg.id,
    pg.monto_pagado,
    COALESCE(SUM(cp.monto_aplicado), 0) AS total_aplicado,
    CASE 
      WHEN COUNT(cp.id) = 0 THEN 'No aplicado'
      WHEN ABS(pg.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0)) < 0.01 THEN 'Completamente aplicado'
      WHEN COALESCE(SUM(cp.monto_aplicado), 0) > pg.monto_pagado THEN 'SOBRE-aplicado'
      ELSE 'Parcialmente aplicado'
    END AS estado_aplicacion
  FROM pagos pg
  LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
  GROUP BY pg.id, pg.monto_pagado
)
SELECT 
  estado_aplicacion,
  COUNT(*) AS cantidad_pagos,
  SUM(monto_pagado) AS suma_monto_pagado,
  SUM(total_aplicado) AS suma_aplicado,
  SUM(monto_pagado) - SUM(total_aplicado) AS diferencia_total,
  ROUND(100.0 * SUM(total_aplicado) / NULLIF(SUM(monto_pagado), 0), 2) AS porcentaje_total_aplicado
FROM aplicacion_pagos
GROUP BY estado_aplicacion
ORDER BY estado_aplicacion;


-- 7. CUOTAS SIN PAGO APLICADO
-- ============================================================================
SELECT 
  c.id AS cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto_cuota,
  c.estado AS estado_cuota,
  COUNT(cp.id) AS pagos_aplicados,
  COALESCE(SUM(cp.monto_aplicado), 0) AS total_pagado
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto_cuota, c.estado
HAVING COUNT(cp.id) = 0 AND c.estado != 'PENDIENTE'
ORDER BY c.prestamo_id, c.numero_cuota;


-- 8. VERIFICACION: Cada pago debe estar en exactamente 1 o mas cuota_pagos
-- ============================================================================
SELECT 
  pg.id AS pago_id,
  pg.monto_pagado,
  COUNT(cp.id) AS aplicaciones_a_cuotas,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_diferentes,
  pg.referencia_pago,
  CASE 
    WHEN COUNT(cp.id) = 0 THEN 'ERROR: Sin aplicacion a cuota'
    WHEN COUNT(cp.id) = 1 THEN 'OK: Una aplicacion'
    WHEN COUNT(DISTINCT cp.cuota_id) = COUNT(cp.id) THEN 'OK: Multiples cuotas (sin duplicados)'
    WHEN COUNT(DISTINCT cp.cuota_id) < COUNT(cp.id) THEN 'WARNING: Duplicados en misma cuota'
    ELSE 'REVISAR'
  END AS validacion
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
GROUP BY pg.id, pg.monto_pagado, pg.referencia_pago
ORDER BY pago_id;


-- 9. RESUMEN POR PRESTAMO: Pagos vs Cuotas
-- ============================================================================
SELECT 
  pre.id AS prestamo_id,
  pre.producto,
  pre.estado,
  pre.total_financiamiento,
  COUNT(DISTINCT c.id) AS cuotas_generadas,
  COUNT(DISTINCT cp.pago_id) AS pagos_aplicados,
  SUM(cp.monto_aplicado) AS suma_pagos_aplicados,
  COUNT(DISTINCT pg.id) AS pagos_unicos,
  SUM(pg.monto_pagado) AS suma_pagos_totales,
  CASE 
    WHEN SUM(pg.monto_pagado) IS NULL THEN 'Sin pagos'
    WHEN ABS(SUM(pg.monto_pagado) - SUM(cp.monto_aplicado)) < 0.01 THEN 'OK: Pagos = Aplicados'
    WHEN SUM(pg.monto_pagado) > SUM(cp.monto_aplicado) THEN 'ERROR: Pagos > Aplicados'
    WHEN SUM(pg.monto_pagado) < SUM(cp.monto_aplicado) THEN 'ERROR: Pagos < Aplicados'
  END AS validacion
FROM prestamos pre
LEFT JOIN cuotas c ON pre.id = c.prestamo_id
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
LEFT JOIN pagos pg ON cp.pago_id = pg.id
GROUP BY pre.id, pre.producto, pre.estado, pre.total_financiamiento
ORDER BY pre.id;


-- 10. ESTADISTICAS FINALES
-- ============================================================================
SELECT 'Pagos totales registrados' AS metrica, COUNT(*)::TEXT AS valor FROM pagos
UNION ALL
SELECT 'Pagos sin asignar a cuotas', COUNT(*)::TEXT 
FROM pagos pg WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pg.id)
UNION ALL
SELECT 'Pagos parcialmente aplicados', COUNT(*)::TEXT
FROM (SELECT pg.id FROM pagos pg LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
      GROUP BY pg.id HAVING COALESCE(SUM(cp.monto_aplicado), 0) > 0 
      AND COALESCE(SUM(cp.monto_aplicado), 0) < pg.monto_pagado) subq
UNION ALL
SELECT 'Pagos completamente aplicados', COUNT(*)::TEXT
FROM (SELECT pg.id FROM pagos pg LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
      GROUP BY pg.id HAVING ABS(pg.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0)) < 0.01
      AND COUNT(cp.id) > 0) subq
UNION ALL
SELECT 'Pagos sobre-aplicados', COUNT(*)::TEXT
FROM (SELECT pg.id FROM pagos pg LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
      GROUP BY pg.id HAVING COALESCE(SUM(cp.monto_aplicado), 0) > pg.monto_pagado) subq
UNION ALL
SELECT 'Total monto pagado registrado', COALESCE(SUM(monto_pagado)::TEXT, '0') FROM pagos
UNION ALL
SELECT 'Total monto aplicado a cuotas', COALESCE(SUM(monto_aplicado)::TEXT, '0') FROM cuota_pagos
UNION ALL
SELECT 'Diferencia no aplicada', 
       COALESCE((SUM(pg.monto_pagado) - COALESCE(SUM(cp.monto_aplicado), 0))::TEXT, '0')
FROM pagos pg LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id;
