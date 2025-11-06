-- ============================================
-- VERIFICAR CRITERIOS PARA CUOTAS ATRASADAS
-- ============================================
-- Este script confirma los criterios exactos que se usan
-- para determinar si una cuota está "Atrasada"
-- ============================================

-- CRITERIOS CONFIRMADOS:
-- 1. La cuota debe estar vencida: fecha_vencimiento < hoy
-- 2. La cuota debe tener pago incompleto: total_pagado < monto_cuota
-- 3. El préstamo debe estar APROBADO: Prestamo.estado = 'APROBADO'
-- ============================================

-- 1. CUOTAS ATRASADAS SEGÚN LOS CRITERIOS DEL SISTEMA
SELECT 
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    CASE 
        WHEN c.total_pagado < c.monto_cuota THEN 'Pago incompleto'
        ELSE 'Pago completo'
    END as estado_pago,
    CASE 
        WHEN c.fecha_vencimiento < CURRENT_DATE THEN 'Vencida'
        ELSE 'No vencida'
    END as estado_vencimiento,
    CASE 
        WHEN c.fecha_vencimiento < CURRENT_DATE 
             AND c.total_pagado < c.monto_cuota 
             AND pr.estado = 'APROBADO' 
        THEN 'SI - Es cuota atrasada'
        ELSE 'NO - No es cuota atrasada'
    END as es_cuota_atrasada
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
ORDER BY c.fecha_vencimiento DESC
LIMIT 20;

-- 2. CONTAR CUOTAS ATRASADAS POR CLIENTE (similar al cálculo del sistema)
SELECT 
    pr.cedula as cedula_cliente,
    COUNT(DISTINCT pr.id) as total_prestamos_aprobados,
    COUNT(CASE 
        WHEN c.fecha_vencimiento < CURRENT_DATE 
             AND c.total_pagado < c.monto_cuota 
        THEN 1 
    END) as cuotas_atrasadas,
    SUM(CASE 
        WHEN c.fecha_vencimiento < CURRENT_DATE 
             AND c.total_pagado < c.monto_cuota 
        THEN (c.capital_pendiente + c.interes_pendiente + COALESCE(c.monto_mora, 0))
        ELSE 0
    END) as saldo_vencido
FROM prestamos pr
INNER JOIN cuotas c ON c.prestamo_id = pr.id
WHERE pr.estado = 'APROBADO'
GROUP BY pr.cedula
HAVING COUNT(CASE 
    WHEN c.fecha_vencimiento < CURRENT_DATE 
         AND c.total_pagado < c.monto_cuota 
    THEN 1 
END) > 0
ORDER BY cuotas_atrasadas DESC
LIMIT 20;

-- 3. RESUMEN DE CRITERIOS
SELECT 
    'Total cuotas' as metrica,
    COUNT(*) as valor
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
UNION ALL
SELECT 
    'Cuotas vencidas' as metrica,
    COUNT(*) as valor
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.fecha_vencimiento < CURRENT_DATE
UNION ALL
SELECT 
    'Cuotas con pago incompleto' as metrica,
    COUNT(*) as valor
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.total_pagado < c.monto_cuota
UNION ALL
SELECT 
    'Cuotas ATRASADAS (vencidas + pago incompleto)' as metrica,
    COUNT(*) as valor
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.fecha_vencimiento < CURRENT_DATE
AND c.total_pagado < c.monto_cuota
UNION ALL
SELECT 
    'Cuotas PAGADAS completamente' as metrica,
    COUNT(*) as valor
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.total_pagado >= c.monto_cuota;

-- 4. EJEMPLOS DE CUOTAS ATRASADAS
SELECT 
    c.id as cuota_id,
    pr.cedula as cedula_cliente,
    pr.id as prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    CURRENT_DATE as fecha_hoy,
    DATEDIFF(CURRENT_DATE, c.fecha_vencimiento) as dias_vencidos,
    c.monto_cuota,
    c.total_pagado,
    (c.monto_cuota - c.total_pagado) as monto_faltante,
    c.estado as estado_cuota,
    '✅ CUMPLE CRITERIOS: fecha_vencimiento < hoy AND total_pagado < monto_cuota' as verificacion
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.fecha_vencimiento < CURRENT_DATE
AND c.total_pagado < c.monto_cuota
ORDER BY c.fecha_vencimiento ASC
LIMIT 10;

-- 5. VERIFICAR CASOS LÍMITE
-- Cuotas vencidas pero completamente pagadas (NO son atrasadas)
SELECT 
    c.id as cuota_id,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    'Vencida pero pagada - NO es atrasada' as observacion
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.fecha_vencimiento < CURRENT_DATE
AND c.total_pagado >= c.monto_cuota
LIMIT 5;

-- Cuotas con pago parcial pero no vencidas (NO son atrasadas)
SELECT 
    c.id as cuota_id,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    'Pago incompleto pero no vencida - NO es atrasada' as observacion
FROM cuotas c
INNER JOIN prestamos pr ON pr.id = c.prestamo_id
WHERE pr.estado = 'APROBADO'
AND c.fecha_vencimiento >= CURRENT_DATE
AND c.total_pagado < c.monto_cuota
LIMIT 5;

