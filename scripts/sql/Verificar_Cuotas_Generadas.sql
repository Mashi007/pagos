-- ============================================================================
-- VERIFICACIÓN DE CUOTAS GENERADAS
-- Ejecutar DESPUÉS de ejecutar Generar_Cuotas_Masivas.py
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar total de cuotas generadas
-- ============================================================================
SELECT 
    'Total cuotas generadas' AS metrica,
    COUNT(*) AS cantidad
FROM cuotas;

-- ============================================================================
-- PASO 2: Préstamos aprobados sin cuotas (debe ser 0 o muy bajo)
-- ============================================================================
SELECT 
    'Préstamos aprobados SIN cuotas' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO' 
    AND c.id IS NULL;

-- ============================================================================
-- PASO 3: Cuotas por préstamo (primeros 10)
-- ============================================================================
SELECT 
    prestamo_id,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL') THEN 1 END) AS cuotas_pendientes,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS saldo_pendiente
FROM cuotas
GROUP BY prestamo_id
ORDER BY prestamo_id
LIMIT 10;

-- ============================================================================
-- PASO 4: Cuotas por estado
-- ============================================================================
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_cuota), 0) AS total_monto_cuota,
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) AS saldo_pendiente
FROM cuotas
GROUP BY estado
ORDER BY estado;

-- ============================================================================
-- PASO 5: Comparar número de cuotas planificadas vs reales
-- ============================================================================
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_reales,
    CASE 
        WHEN p.numero_cuotas = COUNT(c.id) THEN '✅ CORRECTO'
        WHEN COUNT(c.id) = 0 THEN '❌ SIN CUOTAS'
        ELSE '⚠️ INCONSISTENTE'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING p.numero_cuotas != COUNT(c.id) OR COUNT(c.id) = 0
ORDER BY p.id
LIMIT 20;

-- ============================================================================
-- PASO 6: Resumen ejecutivo
-- ============================================================================
SELECT 
    'Total préstamos aprobados' AS metrica,
    COUNT(*) AS valor
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Préstamos con cuotas generadas' AS metrica,
    COUNT(DISTINCT prestamo_id) AS valor
FROM cuotas

UNION ALL

SELECT 
    'Total cuotas generadas' AS metrica,
    COUNT(*) AS valor
FROM cuotas

UNION ALL

SELECT 
    'Cuotas pendientes' AS metrica,
    COUNT(*) AS valor
FROM cuotas
WHERE estado IN ('PENDIENTE', 'ATRASADO', 'PARCIAL')

UNION ALL

SELECT 
    'Cuotas pagadas' AS metrica,
    COUNT(*) AS valor
FROM cuotas
WHERE estado = 'PAGADO';

-- ============================================================================
-- PASO 7: Ejemplo de cuotas generadas (primeros 5 préstamos)
-- ============================================================================
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    p.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

