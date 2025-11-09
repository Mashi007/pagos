-- ============================================================================
-- SCRIPTS SQL PARA CONSULTAR BD - REPORTES FALTANTES
-- ============================================================================
-- Fecha: 2025-11
-- Objetivo: Scripts para consultar datos de los reportes faltantes
-- ============================================================================

-- ============================================================================
-- 1. REPORTE DE MOROSIDAD
-- ============================================================================

-- 1.1. Resumen General de Morosidad
SELECT 
    COUNT(DISTINCT p.id) as total_prestamos_mora,
    COUNT(DISTINCT p.cedula) as total_clientes_mora,
    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
    COALESCE(SUM(c.dias_morosidad), 0) as dias_totales_mora,
    AVG(c.dias_morosidad) as promedio_dias_mora
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.dias_morosidad > 0
  AND c.monto_morosidad > 0
  AND cl.estado != 'INACTIVO';

-- 1.2. Morosidad por Rango de Días
SELECT 
    CASE 
        WHEN c.dias_morosidad BETWEEN 1 AND 30 THEN '1-30 días'
        WHEN c.dias_morosidad BETWEEN 31 AND 60 THEN '31-60 días'
        WHEN c.dias_morosidad BETWEEN 61 AND 90 THEN '61-90 días'
        WHEN c.dias_morosidad BETWEEN 91 AND 180 THEN '91-180 días'
        ELSE 'Más de 180 días'
    END as rango_dias,
    COUNT(DISTINCT p.id) as cantidad_prestamos,
    COUNT(DISTINCT p.cedula) as cantidad_clientes,
    COUNT(c.id) as cantidad_cuotas,
    COALESCE(SUM(c.monto_morosidad), 0) as monto_total
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.dias_morosidad > 0
  AND c.monto_morosidad > 0
  AND cl.estado != 'INACTIVO'
GROUP BY rango_dias
ORDER BY 
    CASE rango_dias
        WHEN '1-30 días' THEN 1
        WHEN '31-60 días' THEN 2
        WHEN '61-90 días' THEN 3
        WHEN '91-180 días' THEN 4
        ELSE 5
    END;

-- 1.3. Morosidad por Analista
SELECT 
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    COUNT(DISTINCT p.id) as cantidad_prestamos,
    COUNT(DISTINCT p.cedula) as cantidad_clientes,
    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
    AVG(c.dias_morosidad) as promedio_dias_mora
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.dias_morosidad > 0
  AND c.monto_morosidad > 0
  AND cl.estado != 'INACTIVO'
GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista')
ORDER BY monto_total_mora DESC;

-- 1.4. Detalle de Préstamos en Mora
SELECT 
    p.id as prestamo_id,
    p.cedula,
    p.nombres,
    p.total_financiamiento,
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    p.concesionario,
    COUNT(c.id) as cuotas_en_mora,
    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
    MAX(c.dias_morosidad) as max_dias_mora,
    MIN(c.fecha_vencimiento) as primera_cuota_vencida
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.dias_morosidad > 0
  AND c.monto_morosidad > 0
  AND cl.estado != 'INACTIVO'
GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento, p.analista, p.producto_financiero, p.concesionario
ORDER BY monto_total_mora DESC;

-- ============================================================================
-- 2. REPORTE FINANCIERO
-- ============================================================================

-- 2.1. Resumen Financiero General
SELECT 
    -- Ingresos (Pagos recibidos)
    COALESCE(SUM(pa.monto_pagado), 0) as total_ingresos,
    COUNT(pa.id) as cantidad_pagos,
    
    -- Cartera Activa
    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
    COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + c.monto_mora), 0) as cartera_pendiente,
    
    -- Morosidad
    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total,
    
    -- Cálculos
    COALESCE(SUM(p.total_financiamiento), 0) - COALESCE(SUM(pa.monto_pagado), 0) as saldo_pendiente,
    CASE 
        WHEN COALESCE(SUM(p.total_financiamiento), 0) > 0 
        THEN (COALESCE(SUM(pa.monto_pagado), 0) / SUM(p.total_financiamiento)) * 100
        ELSE 0
    END as porcentaje_cobrado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id AND c.estado != 'PAGADO'
LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO';

-- 2.2. Ingresos por Mes (Últimos 12 meses)
SELECT 
    DATE_TRUNC('month', pa.fecha_pago) as mes,
    COUNT(pa.id) as cantidad_pagos,
    COALESCE(SUM(pa.monto_pagado), 0) as monto_total
FROM pagos pa
INNER JOIN prestamos p ON p.id = pa.prestamo_id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE pa.activo = true
  AND p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
  AND pa.fecha_pago >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', pa.fecha_pago)
ORDER BY mes DESC;

-- 2.3. Egresos Programados (Cuotas por Vencer)
SELECT 
    DATE_TRUNC('month', c.fecha_vencimiento) as mes,
    COUNT(c.id) as cantidad_cuotas,
    COALESCE(SUM(c.monto_cuota), 0) as monto_programado
FROM cuotas c
INNER JOIN prestamos p ON p.id = c.prestamo_id
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND c.estado != 'PAGADO'
  AND cl.estado != 'INACTIVO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE)
  AND c.fecha_vencimiento < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes;

-- 2.4. Flujo de Caja (Ingresos vs Egresos)
SELECT 
    mes,
    ingresos,
    egresos_programados,
    ingresos - egresos_programados as flujo_neto
FROM (
    SELECT 
        DATE_TRUNC('month', pa.fecha_pago) as mes,
        COALESCE(SUM(pa.monto_pagado), 0) as ingresos,
        0 as egresos_programados
    FROM pagos pa
    INNER JOIN prestamos p ON p.id = pa.prestamo_id
    INNER JOIN clientes cl ON cl.id = p.cliente_id
    WHERE pa.activo = true
      AND p.estado = 'APROBADO'
      AND cl.estado != 'INACTIVO'
      AND pa.fecha_pago >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
    GROUP BY DATE_TRUNC('month', pa.fecha_pago)
    
    UNION ALL
    
    SELECT 
        DATE_TRUNC('month', c.fecha_vencimiento) as mes,
        0 as ingresos,
        COALESCE(SUM(c.monto_cuota), 0) as egresos_programados
    FROM cuotas c
    INNER JOIN prestamos p ON p.id = c.prestamo_id
    INNER JOIN clientes cl ON cl.id = p.cliente_id
    WHERE p.estado = 'APROBADO'
      AND c.estado != 'PAGADO'
      AND cl.estado != 'INACTIVO'
      AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE)
      AND c.fecha_vencimiento < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '12 months'
    GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
) subquery
GROUP BY mes, ingresos, egresos_programados
ORDER BY mes;

-- ============================================================================
-- 3. REPORTE DE ASESORES (ANALISTAS)
-- ============================================================================

-- 3.1. Resumen por Analista
SELECT 
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    COUNT(DISTINCT p.id) as total_prestamos,
    COUNT(DISTINCT p.cedula) as total_clientes,
    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total,
    COALESCE(SUM(pa.monto_pagado), 0) as total_cobrado,
    CASE 
        WHEN COALESCE(SUM(p.total_financiamiento), 0) > 0
        THEN (COALESCE(SUM(pa.monto_pagado), 0) / SUM(p.total_financiamiento)) * 100
        ELSE 0
    END as porcentaje_cobrado,
    CASE 
        WHEN COALESCE(SUM(p.total_financiamiento), 0) > 0
        THEN (COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) / SUM(p.total_financiamiento)) * 100
        ELSE 0
    END as porcentaje_morosidad
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista')
ORDER BY cartera_total DESC;

-- 3.2. Desempeño de Analistas (Últimos 6 meses)
SELECT 
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    DATE_TRUNC('month', p.fecha_aprobacion) as mes,
    COUNT(DISTINCT p.id) as prestamos_aprobados,
    COALESCE(SUM(p.total_financiamiento), 0) as monto_aprobado,
    COALESCE(SUM(pa.monto_pagado), 0) as monto_cobrado
FROM prestamos p
LEFT JOIN pagos pa ON pa.prestamo_id = p.id 
    AND pa.activo = true
    AND DATE_TRUNC('month', pa.fecha_pago) = DATE_TRUNC('month', p.fecha_aprobacion)
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
  AND p.fecha_aprobacion >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '6 months'
GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista'), DATE_TRUNC('month', p.fecha_aprobacion)
ORDER BY analista, mes DESC;

-- 3.3. Clientes por Analista
SELECT 
    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
    p.cedula,
    p.nombres,
    COUNT(DISTINCT p.id) as cantidad_prestamos,
    COALESCE(SUM(p.total_financiamiento), 0) as monto_total_prestamos,
    COALESCE(SUM(pa.monto_pagado), 0) as monto_total_pagado,
    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as monto_mora
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista'), p.cedula, p.nombres
ORDER BY analista, monto_total_prestamos DESC;

-- ============================================================================
-- 4. REPORTE DE PRODUCTOS (MODELOS DE VEHÍCULOS)
-- ============================================================================

-- 4.1. Resumen por Producto/Modelo
SELECT 
    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
    COUNT(DISTINCT p.id) as total_prestamos,
    COUNT(DISTINCT p.cedula) as total_clientes,
    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
    COALESCE(AVG(p.total_financiamiento), 0) as promedio_prestamo,
    COALESCE(SUM(pa.monto_pagado), 0) as total_cobrado,
    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total,
    CASE 
        WHEN COALESCE(SUM(p.total_financiamiento), 0) > 0
        THEN (COALESCE(SUM(pa.monto_pagado), 0) / SUM(p.total_financiamiento)) * 100
        ELSE 0
    END as porcentaje_cobrado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
GROUP BY COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo')
ORDER BY cartera_total DESC;

-- 4.2. Productos por Concesionario
SELECT 
    p.concesionario,
    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
    COUNT(DISTINCT p.id) as cantidad_prestamos,
    COALESCE(SUM(p.total_financiamiento), 0) as monto_total
FROM prestamos p
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
  AND p.concesionario IS NOT NULL
GROUP BY p.concesionario, COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo')
ORDER BY p.concesionario, monto_total DESC;

-- 4.3. Tendencia de Productos (Últimos 12 meses)
SELECT 
    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
    DATE_TRUNC('month', p.fecha_aprobacion) as mes,
    COUNT(DISTINCT p.id) as prestamos_aprobados,
    COALESCE(SUM(p.total_financiamiento), 0) as monto_aprobado
FROM prestamos p
INNER JOIN clientes cl ON cl.id = p.cliente_id
WHERE p.estado = 'APROBADO'
  AND cl.estado != 'INACTIVO'
  AND p.fecha_aprobacion >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
GROUP BY COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo'), DATE_TRUNC('month', p.fecha_aprobacion)
ORDER BY producto, mes DESC;

-- ============================================================================
-- FIN DE SCRIPTS
-- ============================================================================

