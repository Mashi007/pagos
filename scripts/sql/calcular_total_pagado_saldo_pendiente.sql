-- ============================================================================
-- CALCULAR TOTAL PAGADO Y SALDO PENDIENTE
-- ============================================================================
-- Script para calcular el total pagado y saldo pendiente de préstamos
-- Suma las cuotas para generar el total de lo pagado y conocer el saldo a pagar
-- ============================================================================

-- ============================================================================
-- 1. TOTAL PAGADO POR PRÉSTAMO (Suma de cuotas.total_pagado)
-- ============================================================================

SELECT 
    '=== TOTAL PAGADO POR PRÉSTAMO ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado >= c.monto_cuota THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN c.total_pagado < c.monto_cuota THEN 1 END) AS cuotas_pendientes
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento
ORDER BY total_pagado DESC
LIMIT 20;

-- ============================================================================
-- 2. SALDO PENDIENTE POR PRÉSTAMO (Total Financiamiento - Total Pagado)
-- ============================================================================

SELECT 
    '=== SALDO PENDIENTE POR PRÉSTAMO ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado,
    p.total_financiamiento - COALESCE(SUM(c.total_pagado), 0) AS saldo_pendiente,
    CASE 
        WHEN COALESCE(SUM(c.total_pagado), 0) >= p.total_financiamiento THEN '✅ PAGADO COMPLETO'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 THEN '⚠️ SIN PAGOS'
        ELSE '📊 PAGO PARCIAL'
    END AS estado_pago
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento
HAVING p.total_financiamiento - COALESCE(SUM(c.total_pagado), 0) > 0
ORDER BY saldo_pendiente DESC
LIMIT 20;

-- ============================================================================
-- 3. SALDO PENDIENTE DETALLADO (Suma de campos pendientes)
-- ============================================================================

SELECT 
    '=== SALDO PENDIENTE DETALLADO (Capital + Interés + Mora) ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado,
    COALESCE(SUM(c.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(c.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(c.monto_mora), 0) AS mora_pendiente,
    COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) AS saldo_pendiente_total
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
  AND c.estado != 'PAGADO'  -- Solo cuotas no pagadas completamente
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento
HAVING COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) > 0
ORDER BY saldo_pendiente_total DESC
LIMIT 20;

-- ============================================================================
-- 4. TOTAL PAGADO POR CÉDULA (Para comparar con abono_2026)
-- ============================================================================

SELECT 
    '=== TOTAL PAGADO POR CÉDULA (Comparar con abono_2026) ===' AS info;

SELECT 
    p.cedula,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
    a.abonos AS total_abonos_imagen,
    ABS(COALESCE(SUM(c.total_pagado), 0) - COALESCE(a.abonos::numeric, 0)) AS diferencia
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN abono_2026 a ON p.cedula = a.cedula
WHERE p.estado = 'APROBADO'
  AND p.cedula IS NOT NULL
GROUP BY p.cedula, a.abonos
ORDER BY diferencia DESC
LIMIT 20;

-- ============================================================================
-- 5. RESUMEN GENERAL: Total Pagado vs Saldo Pendiente
-- ============================================================================

SELECT 
    '=== RESUMEN GENERAL ===' AS info;

SELECT 
    COUNT(DISTINCT p.id) AS total_prestamos_aprobados,
    COUNT(DISTINCT p.cedula) AS total_clientes,
    COALESCE(SUM(p.total_financiamiento), 0) AS cartera_total,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado_global,
    COALESCE(SUM(p.total_financiamiento), 0) - COALESCE(SUM(c.total_pagado), 0) AS saldo_pendiente_global,
    COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) AS saldo_pendiente_detallado,
    ROUND(
        (COALESCE(SUM(c.total_pagado), 0) / NULLIF(SUM(p.total_financiamiento), 0)) * 100, 
        2
    ) AS porcentaje_pagado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO';

-- ============================================================================
-- 6. EJEMPLO: Préstamo específico con detalle de cuotas
-- ============================================================================

-- ⚠️ REEMPLAZA [PRESTAMO_ID] con el ID del préstamo que quieres consultar
/*
SELECT 
    '=== DETALLE DE CUOTAS PARA PRÉSTAMO [ID] ===' AS info;

SELECT 
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    COALESCE(c.total_pagado, 0) AS total_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.monto_mora,
    c.monto_cuota - COALESCE(c.total_pagado, 0) AS saldo_pendiente_cuota,
    c.estado
FROM cuotas c
WHERE c.prestamo_id = [PRESTAMO_ID]
ORDER BY c.numero_cuota;

-- Resumen del préstamo
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado,
    p.total_financiamiento - COALESCE(SUM(c.total_pagado), 0) AS saldo_pendiente
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.id = [PRESTAMO_ID]
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento;
*/
