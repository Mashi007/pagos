-- ============================================================================
-- VERIFICACION: Todos los pagos estan conciliados correctamente
-- ============================================================================

-- 1. RESUMEN GENERAL: Pagos vs Cuotas
-- ============================================================================
SELECT 
  COUNT(DISTINCT p.id) AS total_pagos,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_con_pagos,
  COUNT(DISTINCT cp.cuota_id) FILTER (WHERE cp.estado = 'PAGADO') AS cuotas_pagadas,
  SUM(CASE WHEN cp.estado = 'PAGADO' THEN cp.monto_cuota ELSE 0 END) AS total_pagado,
  COUNT(DISTINCT pre.id) AS prestamos_totales,
  COUNT(DISTINCT pre.id) FILTER (WHERE pre.estado = 'LIQUIDADO') AS prestamos_liquidados
FROM pago p
LEFT JOIN cuota_pago cp ON p.id = cp.pago_id
LEFT JOIN cuotas cp_tabla ON cp.cuota_id = cp_tabla.id
LEFT JOIN prestamos pre ON cp_tabla.prestamo_id = pre.id;


-- 2. PAGOS NO CONCILIADOS (sin aplicacion a cuotas)
-- ============================================================================
SELECT 
  p.id AS pago_id,
  p.numero_pago,
  p.monto,
  p.fecha_pago,
  p.estado AS estado_pago,
  COUNT(cp.id) AS cuotas_aplicadas
FROM pago p
LEFT JOIN cuota_pago cp ON p.id = cp.pago_id
GROUP BY p.id, p.numero_pago, p.monto, p.fecha_pago, p.estado
HAVING COUNT(cp.id) = 0
ORDER BY p.id;


-- 3. CUOTAS PAGADAS vs ESTADO EN BD
-- ============================================================================
SELECT 
  c.id AS cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto_cuota,
  c.estado AS estado_cuota_en_bd,
  COUNT(cp.id) AS cantidad_pagos_aplicados,
  SUM(cp.monto_cuota) AS total_pagado_en_cuota,
  CASE 
    WHEN c.estado = 'PAGADO' AND SUM(COALESCE(cp.monto_cuota, 0)) >= c.monto_cuota - 0.01 THEN 'OK: Conciliado'
    WHEN c.estado = 'PAGADO' AND SUM(COALESCE(cp.monto_cuota, 0)) < c.monto_cuota - 0.01 THEN 'ERROR: Estado PAGADO pero no 100% pagado'
    WHEN c.estado = 'PENDIENTE' AND SUM(COALESCE(cp.monto_cuota, 0)) > 0 THEN 'ERROR: Estado PENDIENTE pero tiene pagos'
    WHEN c.estado = 'PENDIENTE' AND SUM(COALESCE(cp.monto_cuota, 0)) = 0 THEN 'OK: Pendiente sin pagos'
    ELSE 'REVISAR'
  END AS validacion
FROM cuotas c
LEFT JOIN cuota_pago cp ON c.id = cp.cuota_id
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
  COALESCE(SUM(cp.monto_cuota), 0) AS total_pagado,
  c.monto_cuota - COALESCE(SUM(cp.monto_cuota), 0) AS diferencia,
  CASE 
    WHEN c.estado = 'PAGADO' AND COALESCE(SUM(cp.monto_cuota), 0) < c.monto_cuota - 0.01 
      THEN 'CRITICO: Marcada PAGADO pero no tiene monto completo'
    WHEN c.estado = 'PENDIENTE' AND COALESCE(SUM(cp.monto_cuota), 0) >= c.monto_cuota - 0.01 
      THEN 'ERROR: Marcada PENDIENTE pero está 100% pagada'
    WHEN COALESCE(SUM(cp.monto_cuota), 0) > c.monto_cuota 
      THEN 'ERROR: Pagos exceden monto de cuota'
    ELSE NULL
  END AS tipo_discrepancia
FROM cuotas c
LEFT JOIN cuota_pago cp ON c.id = cp.cuota_id
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto_cuota, c.estado
HAVING (c.estado = 'PAGADO' AND COALESCE(SUM(cp.monto_cuota), 0) < c.monto_cuota - 0.01)
   OR (c.estado = 'PENDIENTE' AND COALESCE(SUM(cp.monto_cuota), 0) >= c.monto_cuota - 0.01)
   OR (COALESCE(SUM(cp.monto_cuota), 0) > c.monto_cuota)
ORDER BY c.prestamo_id, c.numero_cuota;


-- 5. PRESTAMOS: Pagos aplicados vs Capital
-- ============================================================================
SELECT 
  p.id AS prestamo_id,
  p.producto,
  p.estado,
  p.total_financiamiento,
  p.numero_cuotas,
  COUNT(DISTINCT c.id) AS cuotas_generadas,
  COUNT(DISTINCT c.id) FILTER (WHERE c.estado = 'PAGADO') AS cuotas_pagadas,
  COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS total_pagado_en_cuotas,
  p.total_financiamiento - COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS saldo_pendiente,
  CASE 
    WHEN p.estado = 'LIQUIDADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= p.total_financiamiento - 0.01
      THEN 'OK: LIQUIDADO y 100% pagado'
    WHEN p.estado = 'LIQUIDADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) < p.total_financiamiento - 0.01
      THEN 'ERROR: LIQUIDADO pero no 100% pagado'
    WHEN p.estado = 'APROBADO' 
      AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= p.total_financiamiento - 0.01
      THEN 'WARNING: APROBADO pero 100% pagado (debería ser LIQUIDADO)'
    WHEN p.estado = 'APROBADO' THEN 'OK: APROBADO con pagos pendientes'
    ELSE 'REVISAR'
  END AS validacion_conciliacion
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.producto, p.estado, p.total_financiamiento, p.numero_cuotas
ORDER BY p.estado, p.id;


-- 6. DISTRIBUCION: Estados de conciliacion
-- ============================================================================
WITH conciliacion_prestamos AS (
  SELECT 
    p.id,
    p.estado,
    COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS total_pagado,
    p.total_financiamiento,
    CASE 
      WHEN p.estado = 'LIQUIDADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= p.total_financiamiento - 0.01
        THEN 'OK'
      WHEN p.estado = 'LIQUIDADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) < p.total_financiamiento - 0.01
        THEN 'CRITICO: LIQUIDADO sin 100% pago'
      WHEN p.estado = 'APROBADO' 
        AND COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) >= p.total_financiamiento - 0.01
        THEN 'WARNING: Debe actualizarse a LIQUIDADO'
      ELSE 'OK'
    END AS estado_conciliacion
  FROM prestamos p
  LEFT JOIN cuotas c ON p.id = c.prestamo_id
  GROUP BY p.id, p.estado, p.total_financiamiento
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
  p.id AS prestamo_id,
  p.producto,
  COUNT(DISTINCT pago.id) AS total_pagos_registrados,
  SUM(pago.monto) AS suma_pagos,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_con_pagos_aplicados,
  SUM(cp.monto_cuota) AS suma_pagos_aplicados_a_cuotas,
  SUM(pago.monto) - COALESCE(SUM(cp.monto_cuota), 0) AS diferencia_no_aplicada
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN cuota_pago cp ON c.id = cp.cuota_id
LEFT JOIN pago ON cp.pago_id = pago.id
GROUP BY p.id, p.producto
HAVING SUM(pago.monto) - COALESCE(SUM(cp.monto_cuota), 0) != 0
ORDER BY p.id;


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
FROM cuota_pago

UNION ALL

SELECT 
  'Total Pagos registrados' AS metrica,
  COUNT(*)::TEXT
FROM pago

UNION ALL

SELECT 
  'Suma Total de Pagos' AS metrica,
  COALESCE(SUM(monto)::TEXT, '0')
FROM pago

UNION ALL

SELECT 
  'Suma Pagos Aplicados a Cuotas' AS metrica,
  COALESCE(SUM(monto_cuota)::TEXT, '0')
FROM cuota_pago

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
FROM prestamos p
WHERE EXISTS (
  SELECT 1 FROM cuotas c
  WHERE c.prestamo_id = p.id
  GROUP BY c.prestamo_id
  HAVING SUM(CASE WHEN c.estado = 'PAGADO' THEN c.monto_cuota ELSE 0 END) >= p.total_financiamiento - 0.01
);
