-- ============================================================================
-- VERIFICAR INTERÉS Y MORA EN PRÉSTAMOS EXISTENTES
-- ============================================================================
-- Script para verificar que todos los préstamos cumplan con la regla:
-- - tasa_interes = 0.00
-- - monto_mora = 0.00
-- - tasa_mora = 0.00
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR TASA DE INTERÉS EN PRÉSTAMOS
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: TASA DE INTERÉS EN PRÉSTAMOS ===' AS info;

SELECT 
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN tasa_interes = 0 THEN 1 END) AS con_interes_0,
    COUNT(CASE WHEN tasa_interes > 0 THEN 1 END) AS con_interes_mayor_0,
    COUNT(CASE WHEN tasa_interes IS NULL THEN 1 END) AS con_interes_null,
    MIN(tasa_interes) AS tasa_minima,
    MAX(tasa_interes) AS tasa_maxima,
    ROUND(AVG(tasa_interes), 2) AS tasa_promedio
FROM prestamos;

-- Préstamos con interés > 0 (requieren corrección)
SELECT 
    '=== PRÉSTAMOS CON INTERÉS > 0 (REQUIEREN CORRECCIÓN) ===' AS info;

SELECT 
    id,
    cedula,
    nombres,
    total_financiamiento,
    tasa_interes,
    estado,
    fecha_registro
FROM prestamos
WHERE tasa_interes > 0 OR tasa_interes IS NULL
ORDER BY tasa_interes DESC
LIMIT 50;

-- ============================================================================
-- 2. VERIFICAR MORA EN CUOTAS
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN: MORA EN CUOTAS ===' AS info;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN monto_mora = 0 OR monto_mora IS NULL THEN 1 END) AS con_mora_0,
    COUNT(CASE WHEN monto_mora > 0 THEN 1 END) AS con_mora_mayor_0,
    COUNT(CASE WHEN tasa_mora = 0 OR tasa_mora IS NULL THEN 1 END) AS con_tasa_mora_0,
    COUNT(CASE WHEN tasa_mora > 0 THEN 1 END) AS con_tasa_mora_mayor_0,
    COUNT(CASE WHEN dias_mora = 0 OR dias_mora IS NULL THEN 1 END) AS con_dias_mora_0,
    COUNT(CASE WHEN dias_mora > 0 THEN 1 END) AS con_dias_mora_mayor_0,
    MIN(monto_mora) AS mora_minima,
    MAX(monto_mora) AS mora_maxima,
    ROUND(SUM(monto_mora), 2) AS mora_total
FROM cuotas;

-- Cuotas con mora > 0 (requieren corrección)
SELECT 
    '=== CUOTAS CON MORA > 0 (REQUIEREN CORRECCIÓN) ===' AS info;

SELECT 
    c.id,
    c.prestamo_id,
    p.cedula,
    p.nombres,
    c.numero_cuota,
    c.monto_cuota,
    c.monto_mora,
    c.tasa_mora,
    c.dias_mora,
    c.estado,
    c.fecha_vencimiento
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.monto_mora > 0 
   OR c.tasa_mora > 0 
   OR (c.dias_mora > 0 AND c.estado != 'PAGADO')
ORDER BY c.monto_mora DESC, c.prestamo_id, c.numero_cuota
LIMIT 100;

-- ============================================================================
-- 3. RESUMEN POR PRÉSTAMO
-- ============================================================================

SELECT 
    '=== RESUMEN POR PRÉSTAMO ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.tasa_interes,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.monto_mora > 0 THEN 1 END) AS cuotas_con_mora,
    SUM(c.monto_mora) AS mora_total_prestamo,
    MAX(c.tasa_mora) AS tasa_mora_maxima,
    CASE 
        WHEN p.tasa_interes > 0 THEN '⚠️ REQUIERE CORRECCIÓN'
        WHEN SUM(c.monto_mora) > 0 THEN '⚠️ REQUIERE CORRECCIÓN'
        ELSE '✅ CORRECTO'
    END AS estado_validacion
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.tasa_interes > 0 
   OR EXISTS (
       SELECT 1 FROM cuotas c2 
       WHERE c2.prestamo_id = p.id 
       AND (c2.monto_mora > 0 OR c2.tasa_mora > 0)
   )
GROUP BY p.id, p.cedula, p.nombres, p.tasa_interes
ORDER BY mora_total_prestamo DESC, p.tasa_interes DESC
LIMIT 50;

-- ============================================================================
-- 4. ESTADÍSTICAS GENERALES
-- ============================================================================

SELECT 
    '=== ESTADÍSTICAS GENERALES ===' AS info;

SELECT 
    (SELECT COUNT(*) FROM prestamos WHERE tasa_interes > 0) AS prestamos_con_interes,
    (SELECT COUNT(*) FROM prestamos WHERE tasa_interes = 0 OR tasa_interes IS NULL) AS prestamos_sin_interes,
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora > 0) AS cuotas_con_mora,
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora = 0 OR monto_mora IS NULL) AS cuotas_sin_mora,
    (SELECT COUNT(*) FROM cuotas WHERE tasa_mora > 0) AS cuotas_con_tasa_mora,
    (SELECT COUNT(*) FROM cuotas WHERE tasa_mora = 0 OR tasa_mora IS NULL) AS cuotas_sin_tasa_mora,
    (SELECT ROUND(SUM(monto_mora), 2) FROM cuotas WHERE monto_mora > 0) AS mora_total_sistema;
