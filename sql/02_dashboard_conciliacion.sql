-- ============================================================================
-- DASHBOARD DE CONCILIACION: Vistas consolidadas
-- ============================================================================

-- 1. VISTA: Conciliacion General
-- ============================================================================
CREATE OR REPLACE VIEW v_conciliacion_general AS
SELECT 
  (SELECT COUNT(*) FROM pagos) AS total_pagos,
  (SELECT COUNT(DISTINCT pago_id) FROM cuota_pagos) AS pagos_asignados,
  (SELECT COUNT(*) FROM pagos) - (SELECT COUNT(DISTINCT pago_id) FROM cuota_pagos) AS pagos_sin_asignar,
  ROUND(100.0 * (SELECT COUNT(DISTINCT pago_id) FROM cuota_pagos) / NULLIF((SELECT COUNT(*) FROM pagos), 0), 2) AS tasa_asignacion_pct,
  (SELECT COUNT(*) FROM cuotas) AS total_cuotas,
  (SELECT COUNT(*) FROM cuotas WHERE estado = 'PAGADO') AS cuotas_pagadas,
  (SELECT COUNT(*) FROM cuotas WHERE estado = 'PENDIENTE') AS cuotas_pendientes,
  (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
  (SELECT COUNT(*) FROM prestamos WHERE estado = 'LIQUIDADO') AS prestamos_liquidados;


-- 2. VISTA: Distribucion de Pagos
-- ============================================================================
CREATE OR REPLACE VIEW v_distribucion_pagos AS
SELECT 
  'Asignados' AS categoria,
  COUNT(DISTINCT pago_id) AS cantidad,
  SUM(monto_aplicado) AS monto
FROM cuota_pagos
UNION ALL
SELECT 
  'Sin Asignar',
  COUNT(*),
  SUM(monto_pagado)
FROM pagos
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id);


-- 3. VISTA: Estado de Cuotas
-- ============================================================================
CREATE OR REPLACE VIEW v_estado_cuotas AS
SELECT 
  estado,
  COUNT(*) AS cantidad,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS porcentaje,
  SUM(monto_cuota) AS monto_total
FROM cuotas
GROUP BY estado
ORDER BY cantidad DESC;


-- 4. VISTA: Estado de Prestamos
-- ============================================================================
CREATE OR REPLACE VIEW v_estado_prestamos AS
SELECT 
  estado,
  COUNT(*) AS cantidad,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS porcentaje,
  SUM(total_financiamiento) AS capital_total,
  ROUND(AVG(total_financiamiento), 2) AS promedio_capital
FROM prestamos
GROUP BY estado
ORDER BY cantidad DESC;


-- 5. VISTA: Pagos Problematicos
-- ============================================================================
CREATE OR REPLACE VIEW v_pagos_problematicos AS
SELECT 
  'Sin Asignar' AS tipo_problema,
  COUNT(*) AS cantidad,
  SUM(monto_pagado) AS monto_total,
  MIN(fecha_pago) AS fecha_mas_antigua,
  MAX(fecha_pago) AS fecha_mas_reciente
FROM pagos
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id)
UNION ALL
SELECT 
  'Sobre-aplicados',
  COUNT(DISTINCT pago_id),
  SUM(monto_aplicado - (
    SELECT monto_cuota FROM cuotas WHERE id = cp.cuota_id LIMIT 1
  )),
  NULL,
  NULL
FROM cuota_pagos cp
WHERE monto_aplicado > (SELECT monto_cuota FROM cuotas WHERE id = cp.cuota_id);


-- 6. VISTA: Tasa de Conciliacion por Modalidad
-- ============================================================================
CREATE OR REPLACE VIEW v_conciliacion_por_modalidad AS
SELECT 
  p.modalidad_pago,
  COUNT(DISTINCT pg.id) AS total_pagos,
  COUNT(DISTINCT cp.pago_id) AS pagos_asignados,
  COUNT(DISTINCT pg.id) - COUNT(DISTINCT cp.pago_id) AS pagos_sin_asignar,
  ROUND(100.0 * COUNT(DISTINCT cp.pago_id) / NULLIF(COUNT(DISTINCT pg.id), 0), 2) AS tasa_asignacion_pct,
  SUM(pg.monto_pagado) AS suma_pagos,
  SUM(cp.monto_aplicado) AS suma_aplicada
FROM prestamos p
LEFT JOIN pagos pg ON p.id = pg.prestamo_id
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
WHERE p.modalidad_pago IS NOT NULL
GROUP BY p.modalidad_pago
ORDER BY pagos_sin_asignar DESC;


-- 7. VISTA: Dashboard Principal
-- ============================================================================
CREATE OR REPLACE VIEW v_dashboard_principal AS
SELECT 
  'PAGOS' AS seccion,
  'Total' AS metrica,
  (SELECT COUNT(*) FROM pagos)::TEXT AS valor,
  (SELECT ROUND(SUM(monto_pagado), 2)::TEXT FROM pagos) AS monto
UNION ALL
SELECT 'PAGOS', 'Asignados', (SELECT COUNT(DISTINCT pago_id) FROM cuota_pagos)::TEXT, 
  (SELECT ROUND(SUM(monto_aplicado), 2)::TEXT FROM cuota_pagos)
UNION ALL
SELECT 'PAGOS', 'Sin Asignar', 
  (SELECT COUNT(*) FROM pagos WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id))::TEXT,
  (SELECT ROUND(SUM(monto_pagado), 2)::TEXT FROM pagos WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id))
UNION ALL
SELECT 'CUOTAS', 'Total', (SELECT COUNT(*) FROM cuotas)::TEXT, NULL
UNION ALL
SELECT 'CUOTAS', 'Pagadas', (SELECT COUNT(*) FROM cuotas WHERE estado = 'PAGADO')::TEXT, 
  (SELECT ROUND(SUM(monto_cuota), 2)::TEXT FROM cuotas WHERE estado = 'PAGADO')
UNION ALL
SELECT 'CUOTAS', 'Pendientes', (SELECT COUNT(*) FROM cuotas WHERE estado = 'PENDIENTE')::TEXT,
  (SELECT ROUND(SUM(monto_cuota), 2)::TEXT FROM cuotas WHERE estado = 'PENDIENTE')
UNION ALL
SELECT 'PRESTAMOS', 'Total', (SELECT COUNT(*) FROM prestamos)::TEXT,
  (SELECT ROUND(SUM(total_financiamiento), 2)::TEXT FROM prestamos)
UNION ALL
SELECT 'PRESTAMOS', 'Aprobados', (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO')::TEXT,
  (SELECT ROUND(SUM(total_financiamiento), 2)::TEXT FROM prestamos WHERE estado = 'APROBADO')
UNION ALL
SELECT 'PRESTAMOS', 'Liquidados', (SELECT COUNT(*) FROM prestamos WHERE estado = 'LIQUIDADO')::TEXT,
  (SELECT ROUND(SUM(total_financiamiento), 2)::TEXT FROM prestamos WHERE estado = 'LIQUIDADO');


-- ============================================================================
-- USO: Consultar el dashboard principal
-- ============================================================================
-- SELECT * FROM v_dashboard_principal;
-- SELECT * FROM v_conciliacion_general;
-- SELECT * FROM v_pagos_problematicos;
