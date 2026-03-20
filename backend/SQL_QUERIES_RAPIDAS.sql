-- ============================================================================
-- QUERIES RÁPIDAS - Verificación de Pagos en Cuotas (VERSIÓN SIMPLIFICADA)
-- ============================================================================
-- Ejecuta estos queries cuando necesites un diagnóstico rápido
-- ============================================================================

-- ============================================================================
-- 1. ¿CUÁNTOS PAGOS FALTA POR APLICAR? (THE ONE QUERY)
-- ============================================================================
SELECT 
    COUNT(*) as pagos_no_aplicados,
    SUM(p.monto_pagado) as monto_total_no_aplicado,
    MIN(p.fecha_pago) as desde_fecha,
    MAX(p.fecha_pago) as hasta_fecha
FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id
);

-- ============================================================================
-- 2. ¿QUÉ PAGOS ESPECÍFICOS NO ESTÁN EN CUOTA_PAGOS?
-- ============================================================================
SELECT 
    p.id,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    p.estado,
    pr.cedula
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE NOT EXISTS (
    SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id
)
ORDER BY p.fecha_pago DESC
LIMIT 100;

-- ============================================================================
-- 3. ¿QUÉ CUOTAS NO RECIBIERON PAGOS?
-- ============================================================================
SELECT 
    c.id,
    pr.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.estado,
    DATEDIFF(NOW(), c.fecha_vencimiento) as dias_atrasada
FROM cuotas c
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE NOT EXISTS (
    SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id
)
  AND c.estado != 'CANCELADA'
  AND c.estado != 'DESCARTADA'
ORDER BY c.fecha_vencimiento DESC
LIMIT 100;

-- ============================================================================
-- 4. BALANCE GENERAL EN 30 SEGUNDOS
-- ============================================================================
SELECT 
    'Total Pagos' as Item,
    COUNT(*) as Cantidad,
    SUM(monto_pagado) as Monto
FROM pagos
UNION ALL
SELECT 
    'Pagos sin cuotas',
    COUNT(*),
    SUM(monto_pagado)
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
UNION ALL
SELECT 
    'Cuotas sin pagos',
    COUNT(*),
    SUM(monto_cuota)
FROM cuotas c
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id)
UNION ALL
SELECT 
    'Pagos en cuota_pagos',
    COUNT(DISTINCT pago_id),
    SUM(monto_aplicado)
FROM cuota_pagos;

-- ============================================================================
-- 5. POR CLIENTE: ¿QUÉ FALTA PROCESAR?
-- ============================================================================
SELECT 
    pr.cedula,
    COUNT(DISTINCT p.id) as pagos_totales,
    COUNT(DISTINCT CASE WHEN cp.pago_id IS NULL THEN p.id END) as pagos_sin_asignar,
    SUM(CASE WHEN cp.pago_id IS NULL THEN p.monto_pagado ELSE 0 END) as monto_sin_asignar
FROM prestamos pr
LEFT JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY pr.cedula
HAVING pagos_sin_asignar > 0
ORDER BY monto_sin_asignar DESC;

-- ============================================================================
-- 6. PAGOS PARCIALMENTE APLICADOS (Necesitan "completarse")
-- ============================================================================
SELECT 
    p.id,
    p.fecha_pago,
    p.monto_pagado,
    COALESCE(SUM(cp.monto_aplicado), 0) as aplicado,
    p.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0) as falta_aplicar,
    ROUND(100.0 * COALESCE(SUM(cp.monto_aplicado), 0) / p.monto_pagado, 2) as porcentaje
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY p.id
HAVING COALESCE(SUM(cp.monto_aplicado), 0) > 0 
   AND COALESCE(SUM(cp.monto_aplicado), 0) < p.monto_pagado
ORDER BY falta_aplicar DESC;

-- ============================================================================
-- 7. ESTADO DE SALUD: % DE SINCRONIZACIÓN
-- ============================================================================
SELECT 
    ROUND(100.0 * 
        COUNT(DISTINCT CASE WHEN cp.pago_id IS NOT NULL THEN p.id END) / 
        COUNT(DISTINCT p.id), 2) as porcentaje_pagos_sincronizados,
    ROUND(100.0 * 
        COUNT(DISTINCT CASE WHEN cp.cuota_id IS NOT NULL THEN c.id END) / 
        COUNT(DISTINCT c.id), 2) as porcentaje_cuotas_con_pagos
FROM pagos p
CROSS JOIN cuotas c
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id OR c.id = cp.cuota_id;

-- ============================================================================
-- 8. ALERTAS: PAGOS RECIENTES (ÚLTIMOS 7 DÍAS) SIN APLICAR
-- ============================================================================
SELECT 
    p.id,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    DATEDIFF(NOW(), p.fecha_pago) as dias_sin_aplicar
FROM pagos p
WHERE p.fecha_pago >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 9. TOP 10: CLIENTES CON MÁS PAGOS SIN APLICAR
-- ============================================================================
SELECT 
    pr.cedula,
    pr.nombres,
    COUNT(p.id) as cantidad_pagos_sin_aplicar,
    SUM(p.monto_pagado) as monto_total_sin_aplicar,
    COUNT(DISTINCT c.id) as cuotas_sin_pagos
FROM prestamos pr
LEFT JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp2 WHERE cp2.cuota_id = c.id)
GROUP BY pr.cedula
ORDER BY monto_total_sin_aplicar DESC
LIMIT 10;

-- ============================================================================
-- 10. DIAGNÓSTICO RÁPIDO: ¿HAY PROBLEMAS GRAVES?
-- ============================================================================
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ TODOS LOS PAGOS ESTÁN APLICADOS'
        WHEN COUNT(*) < 5 THEN '⚠️  POCOS PAGOS SIN APLICAR - Procesable'
        WHEN COUNT(*) < 50 THEN '⚠️  PAGOS SIN APLICAR - Requiere atención'
        ELSE '🚨 MUCHOS PAGOS SIN APLICAR - Urgente'
    END as diagnostico,
    COUNT(*) as cantidad_pagos_sin_aplicar,
    SUM(monto_pagado) as monto_sin_aplicar,
    MIN(fecha_pago) as mas_antiguo
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id);

-- ============================================================================
-- 11. RANKING: CUOTAS MÁS ATRASADAS SIN PAGOS
-- ============================================================================
SELECT 
    c.id,
    pr.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    DATEDIFF(NOW(), c.fecha_vencimiento) as dias_atrasada,
    c.dias_mora,
    c.estado
FROM cuotas c
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id)
  AND c.estado IN ('ATRASADA', 'VENCIDA', 'PENDIENTE')
ORDER BY c.fecha_vencimiento ASC
LIMIT 20;

-- ============================================================================
-- 12. REPORTE DE CIERRE DIARIO: ¿Qué procesamos hoy?
-- ============================================================================
SELECT 
    DATE(p.fecha_pago) as fecha,
    COUNT(*) as pagos_recibidos,
    SUM(p.monto_pagado) as monto_recibido,
    COUNT(DISTINCT CASE WHEN cp.pago_id IS NOT NULL THEN p.id END) as pagos_procesados,
    COUNT(DISTINCT CASE WHEN cp.pago_id IS NULL THEN p.id END) as pagos_pendientes_procesar,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN cp.pago_id IS NOT NULL THEN p.id END) / COUNT(*), 2) as porcentaje_procesado
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
WHERE p.fecha_pago >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(p.fecha_pago)
ORDER BY fecha DESC;

-- ============================================================================
-- BONUS: SCRIPT PARA IDENTIFICAR PAGOS ESPECÍFICOS
-- ============================================================================
-- Reemplaza 'cedula_aqui' con la cédula del cliente
-- Reemplaza 'referencia_aqui' con la referencia de pago

SELECT 
    p.id,
    p.cedula_cliente,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    COALESCE(SUM(cp.monto_aplicado), 0) as monto_aplicado,
    p.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0) as saldo_no_aplicado,
    STRING_AGG(CAST(cp.cuota_id AS VARCHAR), ', ') as cuotas_aplicadas
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
WHERE p.cedula_cliente = 'cedula_aqui' 
   OR p.referencia_pago = 'referencia_aqui'
GROUP BY p.id
ORDER BY p.fecha_pago DESC;
