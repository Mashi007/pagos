-- ============================================
-- VERIFICACION: Estado de total_pagado en tabla cuotas
-- ============================================
-- Este script verifica si hay datos en la columna total_pagado
-- antes de aplicar los pagos conciliados
-- ============================================

-- ============================================
-- PASO 1: RESUMEN GENERAL
-- ============================================
SELECT 
    'RESUMEN TOTAL_PAGADO EN CUOTAS' AS seccion,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN total_pagado IS NULL THEN 1 END) AS cuotas_con_total_pagado_null,
    COUNT(CASE WHEN total_pagado = 0 OR total_pagado = 0.00 THEN 1 END) AS cuotas_con_total_pagado_cero,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_total_pagado_mayor_cero,
    SUM(CASE WHEN total_pagado > 0 THEN total_pagado ELSE 0 END) AS monto_total_en_total_pagado,
    MIN(total_pagado) AS minimo_total_pagado,
    MAX(total_pagado) AS maximo_total_pagado,
    AVG(total_pagado) AS promedio_total_pagado
FROM cuotas;

-- ============================================
-- PASO 2: CUOTAS CON TOTAL_PAGADO > 0
-- ============================================
SELECT 
    'CUOTAS CON TOTAL_PAGADO > 0' AS seccion,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    c.fecha_vencimiento,
    c.fecha_pago,
    pr.cedula,
    pr.nombres
FROM cuotas c
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE c.total_pagado > 0
ORDER BY c.total_pagado DESC
LIMIT 50;

-- ============================================
-- PASO 3: RESUMEN POR PRESTAMO
-- ============================================
SELECT 
    'RESUMEN POR PRESTAMO' AS seccion,
    c.prestamo_id,
    pr.cedula,
    pr.nombres,
    COUNT(*) AS total_cuotas_prestamo,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
    SUM(c.total_pagado) AS monto_total_pagado_prestamo,
    SUM(c.monto_cuota) AS monto_total_cuotas_prestamo
FROM cuotas c
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE c.total_pagado > 0
GROUP BY c.prestamo_id, pr.cedula, pr.nombres
ORDER BY monto_total_pagado_prestamo DESC
LIMIT 50;

-- ============================================
-- PASO 4: VERIFICACION DE ESTADO
-- ============================================
SELECT 
    'VERIFICACION ESTADO CUOTAS' AS seccion,
    c.estado,
    COUNT(*) AS cantidad_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS con_total_pagado_mayor_cero,
    SUM(c.total_pagado) AS monto_total_pagado
FROM cuotas c
GROUP BY c.estado
ORDER BY cantidad_cuotas DESC;

-- ============================================
-- PASO 5: VERIFICACION DE FECHA_PAGO
-- ============================================
SELECT 
    'VERIFICACION FECHA_PAGO' AS seccion,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS cuotas_con_fecha_pago,
    COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS cuotas_sin_fecha_pago,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND total_pagado > 0 THEN 1 END) AS cuotas_con_fecha_y_pago,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND total_pagado = 0 THEN 1 END) AS cuotas_con_fecha_sin_pago
FROM cuotas;
