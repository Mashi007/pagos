-- ============================================================================
-- VERIFICACION INTEGRAL: Todos los prestamos tienen cuotas generadas
-- ============================================================================

-- 1. RESUMEN GENERAL: Prestamos vs Cuotas
-- ============================================================================
SELECT 
  COUNT(DISTINCT p.id) AS total_prestamos,
  COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
  COUNT(DISTINCT p.id) FILTER (WHERE c.prestamo_id IS NULL) AS prestamos_sin_cuotas,
  COUNT(c.id) AS total_cuotas,
  ROUND(AVG(c.numero_cuota), 2) AS promedio_cuotas_por_prestamo
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id;


-- 2. PRESTAMOS SIN CUOTAS (deben ser 0)
-- ============================================================================
SELECT 
  p.id,
  p.cliente_id,
  p.referencia_interna,
  p.estado,
  p.total_financiamiento,
  p.numero_cuotas,
  p.fecha_aprobacion,
  COUNT(c.id) AS cuotas_generadas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.cliente_id, p.referencia_interna, p.estado, 
         p.total_financiamiento, p.numero_cuotas, p.fecha_aprobacion
HAVING COUNT(c.id) = 0
ORDER BY p.id;


-- 3. VERIFICACION: numero_cuotas vs cuotas realmente generadas
-- ============================================================================
SELECT 
  p.id,
  p.numero_cuotas AS numero_cuotas_esperado,
  COUNT(c.id) AS cuotas_generadas,
  CASE 
    WHEN COUNT(c.id) = p.numero_cuotas THEN 'OK: Coinciden'
    WHEN COUNT(c.id) > p.numero_cuotas THEN 'ERROR: Mas cuotas que lo esperado'
    WHEN COUNT(c.id) < p.numero_cuotas THEN 'ERROR: Menos cuotas que lo esperado'
    WHEN COUNT(c.id) = 0 THEN 'ERROR: Sin cuotas'
  END AS estado_cobertura
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.numero_cuotas
ORDER BY estado_cobertura DESC, p.id;


-- 4. DISTRIBUCION: Prestamos agrupados por cobertura de cuotas
-- ============================================================================
WITH cobertura_cuotas AS (
  SELECT 
    p.id,
    p.numero_cuotas,
    COUNT(c.id) AS cuotas_reales,
    CASE 
      WHEN COUNT(c.id) = p.numero_cuotas THEN 'Completa'
      WHEN COUNT(c.id) = 0 THEN 'Sin cuotas'
      ELSE 'Parcial'
    END AS tipo_cobertura
  FROM prestamos p
  LEFT JOIN cuotas c ON p.id = c.prestamo_id
  GROUP BY p.id, p.numero_cuotas
)
SELECT 
  tipo_cobertura,
  COUNT(*) AS cantidad_prestamos,
  MIN(numero_cuotas) AS min_cuotas_esperadas,
  MAX(numero_cuotas) AS max_cuotas_esperadas,
  ROUND(AVG(numero_cuotas), 2) AS promedio_cuotas_esperadas
FROM cobertura_cuotas
GROUP BY tipo_cobertura
ORDER BY tipo_cobertura;


-- 5. DETALLE DE PRESTAMOS CON COBERTURA INCOMPLETA
-- ============================================================================
SELECT 
  p.id,
  p.cliente_id,
  p.referencia_interna,
  p.estado,
  p.numero_cuotas AS cuotas_esperadas,
  COUNT(c.id) AS cuotas_generadas,
  p.numero_cuotas - COUNT(c.id) AS cuotas_faltantes,
  ROUND(100.0 * COUNT(c.id) / NULLIF(p.numero_cuotas, 0), 2) AS porcentaje_cobertura
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.cliente_id, p.referencia_interna, p.estado, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas
ORDER BY p.id;


-- 6. VALIDACION: Secuencia de numero_cuota (debe ser 1, 2, 3, ...)
-- ============================================================================
WITH cuota_secuencia AS (
  SELECT 
    prestamo_id,
    COUNT(*) AS cuotas_totales,
    COUNT(DISTINCT numero_cuota) AS cuotas_unicas,
    MIN(numero_cuota) AS min_numero,
    MAX(numero_cuota) AS max_numero,
    CASE 
      WHEN MIN(numero_cuota) = 1 AND MAX(numero_cuota) = COUNT(*) THEN 'Secuencia OK'
      ELSE 'Secuencia INVALIDA'
    END AS validacion_secuencia
  FROM cuotas
  GROUP BY prestamo_id
)
SELECT 
  prestamo_id,
  cuotas_totales,
  cuotas_unicas,
  min_numero,
  max_numero,
  validacion_secuencia,
  CASE 
    WHEN validacion_secuencia = 'Secuencia INVALIDA' THEN 'REVISAR: Secuencia discontinua o no empieza en 1'
    WHEN cuotas_totales != cuotas_unicas THEN 'REVISAR: Hay duplicados'
    ELSE 'OK'
  END AS estado_final
FROM cuota_secuencia
WHERE validacion_secuencia = 'Secuencia INVALIDA' 
   OR cuotas_totales != cuotas_unicas
ORDER BY prestamo_id;


-- 7. ESTADISTICAS FINALES: Estados de prestamos
-- ============================================================================
SELECT 
  p.estado,
  COUNT(*) AS cantidad_prestamos,
  COUNT(*) FILTER (WHERE c.id IS NOT NULL) AS con_cuotas,
  COUNT(*) FILTER (WHERE c.id IS NULL) AS sin_cuotas,
  ROUND(100.0 * COUNT(*) FILTER (WHERE c.id IS NOT NULL) / COUNT(*), 2) AS porcentaje_con_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.estado
ORDER BY p.estado;


-- 8. RESUMEN EJECUTIVO
-- ============================================================================
SELECT 
  'Total Préstamos' AS metrica,
  COUNT(DISTINCT p.id)::TEXT AS valor
FROM prestamos p

UNION ALL

SELECT 
  'Préstamos CON cuotas' AS metrica,
  COUNT(DISTINCT c.prestamo_id)::TEXT AS valor
FROM cuotas c

UNION ALL

SELECT 
  'Préstamos SIN cuotas' AS metrica,
  (SELECT COUNT(*) FROM prestamos p 
   WHERE NOT EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id))::TEXT AS valor

UNION ALL

SELECT 
  'Total Cuotas' AS metrica,
  COUNT(*)::TEXT AS valor
FROM cuotas

UNION ALL

SELECT 
  'Préstamos con cobertura completa' AS metrica,
  COUNT(*)::TEXT AS valor
FROM (
  SELECT p.id
  FROM prestamos p
  LEFT JOIN cuotas c ON p.id = c.prestamo_id
  GROUP BY p.id, p.numero_cuotas
  HAVING COUNT(c.id) = p.numero_cuotas
) subq

UNION ALL

SELECT 
  'Préstamos con cobertura parcial' AS metrica,
  COUNT(*)::TEXT AS valor
FROM (
  SELECT p.id
  FROM prestamos p
  LEFT JOIN cuotas c ON p.id = c.prestamo_id
  GROUP BY p.id, p.numero_cuotas
  HAVING COUNT(c.id) > 0 AND COUNT(c.id) < p.numero_cuotas
) subq;
