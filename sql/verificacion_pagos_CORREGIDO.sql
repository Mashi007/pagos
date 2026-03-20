-- ============================================================================
-- VERIFICACION: Todos los pagos estan conciliados correctamente
-- COLUMNAS CORRECTAS: pagos (tabla), pagos.monto_pagado, cuota_pagos.monto_aplicado
-- ============================================================================

-- 1. RESUMEN GENERAL: Pagos vs Cuotas
-- ============================================================================
SELECT 
  COUNT(DISTINCT pg.id) AS total_pagos_registrados,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_con_pagos_aplicados,
  COUNT(DISTINCT c.id) FILTER (WHERE c.estado = 'PAGADO') AS cuotas_en_estado_pagado,
  SUM(CASE WHEN c.estado = 'PAGADO' THEN c.monto_cuota ELSE 0 END) AS total_pagado_por_cuotas,
  COUNT(DISTINCT pre.id) AS prestamos_totales,
  COUNT(DISTINCT pre.id) FILTER (WHERE pre.estado = 'LIQUIDADO') AS prestamos_liquidados
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
LEFT JOIN cuotas c ON cp.cuota_id = c.id
LEFT JOIN prestamos pre ON c.prestamo_id = pre.id;


-- 2. PAGOS NO CONCILIADOS (sin aplicacion a cuotas)
-- ============================================================================
SELECT 
  pg.id AS pago_id,
  pg.prestamo_id,
  pg.cedula,
  pg.fecha_pago,
  pg.monto_pagado,
  pg.referencia_pago,
  COUNT(cp.id) AS cuotas_aplicadas_a
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
GROUP BY pg.id, pg.prestamo_id, pg.cedula, pg.fecha_pago, pg.monto_pagado, pg.referencia_pago
HAVING COUNT(cp.id) = 0
ORDER BY pg.id;


-- 3. CUOTAS PAGADAS vs ESTADO EN BD
-- ============================================================================
SELECT 
  c.id AS cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto_cuota,
  c.estado AS estado_cuota_en_bd,
  COUNT(cp.id) AS cantidad_pagos_aplicados,
  SUM(cp.monto_aplicado) AS total_pagado_en_cuota,
  CASE 
    WHEN c.estado = 'PAGADO' AND SUM(COALESCE(cp.monto_aplicado, 0)) >= c.monto_cuota - 0.01 THEN 'OK: Conciliado'
    WHEN c.estado = 'PAGADO' AND SUM(COALESCE(cp.monto_aplicado, 0)) < c.monto_cuota - 0.01 THEN 'ERROR: Estado PAGADO pero no 100% pagado'
    WHEN c.estado = 'PENDIENTE' AND SUM(COALESCE(cp.monto_aplicado, 0)) > 0 THEN 'ERROR: Estado PENDIENTE pero tiene pagos'
    WHEN c.estado = 'PENDIENTE' AND SUM(COALESCE(cp.monto_aplicado, 0)) = 0 THEN 'OK: Pendiente sin pagos'
    ELSE 'REVISAR'
  END AS validacion
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto_cuota, c.estado
ORDER BY c.prestamo_id, c.numero_cuota;


-- 4. CUOTAS CON DISCREPANCIAS
-- ============================================================================
SELECT 
  c.id AS cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto_cuota,
  c.estado AS estado_en_bd,
  COALESCE(SUM(cp.monto_aplicado), 0) AS total_pagado,
  c.monto_cuota - COALESCE(SUM(cp.monto_aplicado), 0) AS diferencia,
  CASE 
    WHEN c.estado = 'PAGADO' AND COALESCE(SUM(cp.monto_aplicado), 0) < c.monto_cuota - 0.01 
      THEN 'CRITICO: Marcada PAGADO pero no tiene monto completo'
    WHEN c.estado = 'PENDIENTE' AND COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto_cuota - 0.01 
      THEN 'ERROR: Marcada PENDIENTE pero esta 100% pagada'
    WHEN COALESCE(SUM(cp.monto_aplicado), 0) > c.monto_cuota 
      THEN 'ERROR: Pagos exceden monto de cuota'
    ELSE NULL
  END AS tipo_discrepancia
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto_cuota, c.estado
HAVING (c.estado = 'PAGADO' AND COALESCE(SUM(cp.monto_aplicado), 0) < c.monto_cuota - 0.01)
   OR (c.estado = 'PENDIENTE' AND COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto_cuota - 0.01)
   OR (COALESCE(SUM(cp.monto_aplicado), 0) > c.monto_cuota)
ORDER BY c.prestamo_id, c.numero_cuota;


-- 5. PRESTAMOS: Pagos aplicados vs Capital
-- ============================================================================
SELECT 
  pre.id AS prestamo_id,
  pre.producto,
  pre.estado,
  pre.total_financiamiento,
  pre.numero_cuotas,
  COUNT(DISTINCT c.id) AS cuotas_generadas,
  COUNT(DISTINCT c.id) FILTER (WHERE c.estado = 'PAGADO') AS cuotas_pagadas,
  COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS total_pagado_en_cuotas,
  pre.total_financiamiento - COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS saldo_pendiente,
  CASE 
    WHEN pre.estado = 'LIQUIDADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= pre.total_financiamiento - 0.01
      THEN 'OK: LIQUIDADO y 100% pagado'
    WHEN pre.estado = 'LIQUIDADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) < pre.total_financiamiento - 0.01
      THEN 'ERROR: LIQUIDADO pero no 100% pagado'
    WHEN pre.estado = 'APROBADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= pre.total_financiamiento - 0.01
      THEN 'WARNING: APROBADO pero 100% pagado (deberia ser LIQUIDADO)'
    WHEN pre.estado = 'APROBADO' THEN 'OK: APROBADO con pagos pendientes'
    ELSE 'REVISAR'
  END AS validacion_conciliacion
FROM prestamos pre
LEFT JOIN cuotas c ON pre.id = c.prestamo_id
GROUP BY pre.id, pre.producto, pre.estado, pre.total_financiamiento, pre.numero_cuotas
ORDER BY pre.estado, pre.id;


-- 6. DISTRIBUCION: Estados de conciliacion
-- ============================================================================
WITH conciliacion_prestamos AS (
  SELECT 
    pre.id,
    pre.estado,
    COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS total_pagado,
    pre.total_financiamiento,
    CASE 
      WHEN pre.estado = 'LIQUIDADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= pre.total_financiamiento - 0.01
        THEN 'OK'
      WHEN pre.estado = 'LIQUIDADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) < pre.total_financiamiento - 0.01
        THEN 'CRITICO: LIQUIDADO sin 100% pago'
      WHEN pre.estado = 'APROBADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= pre.total_financiamiento - 0.01
        THEN 'WARNING: Debe actualizarse a LIQUIDADO'
      ELSE 'OK'
    END AS estado_conciliacion
  FROM prestamos pre
  LEFT JOIN cuotas c ON pre.id = c.prestamo_id
  GROUP BY pre.id, pre.estado, pre.total_financiamiento
)
SELECT 
  estado_conciliacion,
  COUNT(*) AS cantidad_prestamos,
  COUNT(*) FILTER (WHERE estado = 'APROBADO') AS aprobados,
  COUNT(*) FILTER (WHERE estado = 'LIQUIDADO') AS liquidados
FROM conciliacion_prestamos
GROUP BY estado_conciliacion
ORDER BY estado_conciliacion;


-- 7. PAGOS: Resumen por prestamo
-- ============================================================================
SELECT 
  pre.id AS prestamo_id,
  pre.producto,
  COUNT(DISTINCT pg.id) AS total_pagos_registrados,
  SUM(pg.monto_pagado) AS suma_pagos,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_con_pagos_aplicados,
  SUM(cp.monto_aplicado) AS suma_pagos_aplicados_a_cuotas,
  SUM(pg.monto_pagado) - COALESCE(SUM(cp.monto_aplicado), 0) AS diferencia_no_aplicada
FROM prestamos pre
LEFT JOIN cuotas c ON pre.id = c.prestamo_id
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
LEFT JOIN pagos pg ON cp.pago_id = pg.id
GROUP BY pre.id, pre.producto
HAVING SUM(pg.monto_pagado) - COALESCE(SUM(cp.monto_aplicado), 0) != 0
ORDER BY pre.id;


-- 8. ESTADISTICAS FINALES
-- ============================================================================
SELECT 
  'Total Cuotas' AS metrica,
  COUNT(*)::TEXT AS valor
FROM cuotas

UNION ALL

SELECT 
  'Cuotas PAGADAS (estado=PAGADO)' AS metrica,
  COUNT(*)::TEXT
FROM cuotas WHERE estado = 'PAGADO'

UNION ALL

SELECT 
  'Cuotas PENDIENTES (estado=PENDIENTE)' AS metrica,
  COUNT(*)::TEXT
FROM cuotas WHERE estado = 'PENDIENTE'

UNION ALL

SELECT 
  'Cuotas con pagos aplicados' AS metrica,
  COUNT(DISTINCT cuota_id)::TEXT
FROM cuota_pagos

UNION ALL

SELECT 
  'Total Pagos registrados' AS metrica,
  COUNT(*)::TEXT
FROM pagos

UNION ALL

SELECT 
  'Suma Total Monto Pagado' AS metrica,
  COALESCE(SUM(monto_pagado)::TEXT, '0')
FROM pagos

UNION ALL

SELECT 
  'Suma Pagos Aplicados a Cuotas' AS metrica,
  COALESCE(SUM(monto_aplicado)::TEXT, '0')
FROM cuota_pagos

UNION ALL

SELECT 
  'Prestamos APROBADO' AS metrica,
  COUNT(*)::TEXT
FROM prestamos WHERE estado = 'APROBADO'

UNION ALL

SELECT 
  'Prestamos LIQUIDADO' AS metrica,
  COUNT(*)::TEXT
FROM prestamos WHERE estado = 'LIQUIDADO'

UNION ALL

SELECT 
  'Prestamos 100% Pagados' AS metrica,
  COUNT(*)::TEXT
FROM prestamos pre
WHERE EXISTS (
  SELECT 1 FROM cuotas c
  WHERE c.prestamo_id = pre.id
  GROUP BY c.prestamo_id
  HAVING SUM(CASE WHEN c.estado = 'PAGADO' THEN c.monto_cuota ELSE 0 END) >= pre.total_financiamiento - 0.01
);
