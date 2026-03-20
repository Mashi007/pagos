-- ============================================================================
-- VERIFICACIÓN INTEGRAL: ¿Están todos los pagos cargados en sus cuotas?
-- ============================================================================
-- Este conjunto de queries verifica la consistencia entre pagos y cuotas
-- usando la tabla cuota_pagos como registro del historial de aplicaciones.
-- ============================================================================

-- ============================================================================
-- 1. RESUMEN GENERAL: ¿Qué pagos NO están vinculados a ninguna cuota?
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    p.estado,
    COALESCE(SUM(cp.monto_aplicado), 0) as total_aplicado_a_cuotas,
    p.monto_pagado - COALESCE(SUM(cp.monto_aplicado), 0) as diferencia_no_aplicada
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY p.id
HAVING COALESCE(SUM(cp.monto_aplicado), 0) < p.monto_pagado
   OR COALESCE(SUM(cp.monto_aplicado), 0) = 0
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 2. PAGOS COMPLETAMENTE DESCARGADOS (aplicados 100% a cuotas)
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    COUNT(DISTINCT cp.cuota_id) as numero_cuotas_aplicado,
    SUM(cp.monto_aplicado) as total_aplicado,
    p.monto_pagado - SUM(cp.monto_aplicado) as saldo_sin_aplicar
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY p.id
HAVING SUM(cp.monto_aplicado) >= p.monto_pagado
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 3. PAGOS PARCIALMENTE APLICADOS (ni completamente ni sin aplicar)
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    SUM(cp.monto_aplicado) as total_aplicado,
    p.monto_pagado - SUM(cp.monto_aplicado) as saldo_pendiente,
    ROUND(100.0 * SUM(cp.monto_aplicado) / p.monto_pagado, 2) as porcentaje_aplicado,
    COUNT(DISTINCT cp.cuota_id) as numero_cuotas
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
WHERE cp.pago_id IS NOT NULL
GROUP BY p.id
HAVING SUM(cp.monto_aplicado) > 0 
   AND SUM(cp.monto_aplicado) < p.monto_pagado
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 4. PAGOS SIN REGISTRO EN CUOTA_PAGOS (riesgo: completamente perdidos)
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    p.estado,
    'PAGO PERDIDO - NO EXISTE EN CUOTA_PAGOS' as estado_carga
FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id
)
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 5. PAGOS CON REFERENCIA PAGO (válidos) vs SIN REFERENCIA (inválidos)
-- ============================================================================
SELECT 
    CASE 
        WHEN p.referencia_pago IS NULL OR p.referencia_pago = '' THEN 'SIN REFERENCIA'
        ELSE 'CON REFERENCIA'
    END as tipo_referencia,
    COUNT(*) as cantidad_pagos,
    COALESCE(SUM(p.monto_pagado), 0) as total_monto,
    SUM(CASE WHEN cp.pago_id IS NULL THEN 1 ELSE 0 END) as sin_cuota_asignada,
    SUM(CASE WHEN cp.pago_id IS NOT NULL THEN 1 ELSE 0 END) as con_cuota_asignada
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY tipo_referencia;

-- ============================================================================
-- 6. PAGOS POR ESTADO Y SU COBERTURA EN CUOTAS
-- ============================================================================
SELECT 
    p.estado,
    COUNT(*) as total_pagos,
    SUM(p.monto_pagado) as total_monto,
    SUM(CASE WHEN cp.pago_id IS NOT NULL THEN 1 ELSE 0 END) as con_cuotas,
    SUM(CASE WHEN cp.pago_id IS NULL THEN 1 ELSE 0 END) as sin_cuotas,
    ROUND(100.0 * SUM(CASE WHEN cp.pago_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as porcentaje_asignado
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
GROUP BY p.estado
ORDER BY total_pagos DESC;

-- ============================================================================
-- 7. ANÁLISIS POR PRÉSTAMO: ¿Todas sus cuotas reciben pagos?
-- ============================================================================
SELECT 
    pr.id as prestamo_id,
    pr.cedula,
    pr.monto_solicitado,
    COUNT(DISTINCT c.id) as total_cuotas,
    SUM(CASE WHEN cp.cuota_id IS NOT NULL THEN 1 ELSE 0 END) as cuotas_con_pagos,
    COUNT(DISTINCT c.id) - SUM(CASE WHEN cp.cuota_id IS NOT NULL THEN 1 ELSE 0 END) as cuotas_sin_pagos,
    COUNT(DISTINCT p.id) as total_pagos_asignados,
    SUM(p.monto_pagado) as total_monto_pagado
FROM prestamos pr
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
LEFT JOIN pagos p ON cp.pago_id = p.id
GROUP BY pr.id
HAVING COUNT(DISTINCT c.id) > SUM(CASE WHEN cp.cuota_id IS NOT NULL THEN 1 ELSE 0 END)
ORDER BY cuotas_sin_pagos DESC;

-- ============================================================================
-- 8. CUOTAS SIN PAGOS ASIGNADOS (riesgo: cuotas olvidadas)
-- ============================================================================
SELECT 
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.estado,
    c.total_pagado,
    pr.cedula,
    pr.monto_solicitado
FROM cuotas c
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE NOT EXISTS (
    SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id
)
ORDER BY c.fecha_vencimiento DESC;

-- ============================================================================
-- 9. DUPLICADOS: Pagos aplicados a la MISMA cuota múltiples veces
-- ============================================================================
SELECT 
    cp.cuota_id,
    COUNT(*) as cantidad_veces_aplicado,
    STRING_AGG(CAST(cp.pago_id AS VARCHAR), ', ') as pago_ids,
    SUM(cp.monto_aplicado) as total_monto_aplicado,
    c.monto_cuota
FROM cuota_pagos cp
JOIN cuotas c ON cp.cuota_id = c.id
GROUP BY cp.cuota_id
HAVING COUNT(*) > 1
ORDER BY cantidad_veces_aplicado DESC;

-- ============================================================================
-- 10. INCONSISTENCIAS: Monto total en cuota_pagos vs monto_cuota
-- ============================================================================
SELECT 
    c.id as cuota_id,
    c.numero_cuota,
    c.monto_cuota,
    COALESCE(SUM(cp.monto_aplicado), 0) as total_pagado_registrado,
    c.monto_cuota - COALESCE(SUM(cp.monto_aplicado), 0) as saldo_restante,
    c.estado,
    pr.cedula
FROM cuotas c
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE COALESCE(SUM(cp.monto_aplicado), 0) != c.total_pagado
   OR (c.estado = 'PAGADA' AND COALESCE(SUM(cp.monto_aplicado), 0) < c.monto_cuota)
   OR (c.estado IN ('PENDIENTE', 'ATRASADA') AND COALESCE(SUM(cp.monto_aplicado), 0) > 0)
GROUP BY c.id
ORDER BY c.fecha_vencimiento DESC;

-- ============================================================================
-- 11. REPORTE EJECUTIVO: DASHBOARD DE SINCRONIZACIÓN
-- ============================================================================
SELECT 
    'Total Pagos' as metrica,
    COUNT(*) as cantidad
FROM pagos
UNION ALL
SELECT 
    'Pagos con cuotas asignadas',
    COUNT(DISTINCT p.id)
FROM pagos p
WHERE EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
UNION ALL
SELECT 
    'Pagos SIN cuotas asignadas',
    COUNT(DISTINCT p.id)
FROM pagos p
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
UNION ALL
SELECT 
    'Total Cuotas',
    COUNT(*)
FROM cuotas
UNION ALL
SELECT 
    'Cuotas con pagos asignados',
    COUNT(DISTINCT cp.cuota_id)
FROM cuota_pagos cp
UNION ALL
SELECT 
    'Cuotas SIN pagos asignados',
    COUNT(*)
FROM cuotas c
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id)
UNION ALL
SELECT 
    'Registros en cuota_pagos',
    COUNT(*)
FROM cuota_pagos
UNION ALL
SELECT 
    'Monto Total Pagos (BD)',
    CAST(COALESCE(SUM(monto_pagado), 0) AS VARCHAR)
FROM pagos
UNION ALL
SELECT 
    'Monto Total Cuotas (BD)',
    CAST(COALESCE(SUM(monto_cuota), 0) AS VARCHAR)
FROM cuotas;

-- ============================================================================
-- 12. QUERY PARA ENCONTRAR PAGOS HUÉRFANOS (sin préstamo válido)
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    CASE 
        WHEN p.prestamo_id IS NULL THEN 'Sin préstamo asignado'
        WHEN NOT EXISTS (SELECT 1 FROM prestamos pr WHERE pr.id = p.prestamo_id) THEN 'Préstamo no existe'
        ELSE 'OK'
    END as validez_prestamo,
    COUNT(DISTINCT cp.cuota_id) as cuotas_asignadas
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
WHERE p.prestamo_id IS NULL 
   OR NOT EXISTS (SELECT 1 FROM prestamos pr WHERE pr.id = p.prestamo_id)
GROUP BY p.id
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- 13. RESUMEN POR CLIENTE: ¿Sincronizados sus pagos y cuotas?
-- ============================================================================
SELECT 
    pr.cedula,
    COUNT(DISTINCT p.id) as total_pagos,
    SUM(p.monto_pagado) as monto_pagado,
    COUNT(DISTINCT c.id) as total_cuotas,
    SUM(c.monto_cuota) as monto_cuotas,
    COUNT(DISTINCT cp.pago_id) as pagos_asignados_a_cuotas,
    COUNT(DISTINCT c.id) - COUNT(DISTINCT CASE WHEN cp.cuota_id IS NOT NULL THEN c.id END) as cuotas_sin_pago,
    ROUND(100.0 * COUNT(DISTINCT cp.pago_id) / COUNT(DISTINCT p.id), 2) as porcentaje_pagos_asignados
FROM prestamos pr
LEFT JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
GROUP BY pr.cedula
HAVING COUNT(DISTINCT p.id) > 0
ORDER BY porcentaje_pagos_asignados ASC;

-- ============================================================================
-- 14. AUDIT: Pagos recientes sin cuotas asignadas (últimos 30 días)
-- ============================================================================
SELECT 
    p.id,
    p.prestamo_id,
    p.cedula,
    p.fecha_pago,
    p.monto_pagado,
    p.referencia_pago,
    p.estado,
    CASE 
        WHEN cp.pago_id IS NULL THEN 'SIN ASIGNAR'
        ELSE 'ASIGNADO'
    END as estado_carga,
    NOW() - p.fecha_pago as tiempo_sin_asignar
FROM pagos p
LEFT JOIN cuota_pagos cp ON p.id = cp.pago_id
WHERE p.fecha_pago >= NOW() - INTERVAL '30 days'
  AND cp.pago_id IS NULL
ORDER BY p.fecha_pago DESC;

-- ============================================================================
-- ÍNDICES RECOMENDADOS PARA OPTIMIZAR ESTAS QUERIES
-- ============================================================================
/*
CREATE INDEX idx_pagos_prestamo_id ON pagos(prestamo_id);
CREATE INDEX idx_pagos_cedula ON pagos(cedula_cliente);
CREATE INDEX idx_cuotas_prestamo_id ON cuotas(prestamo_id);
CREATE INDEX idx_cuota_pagos_pago_id ON cuota_pagos(pago_id);
CREATE INDEX idx_cuota_pagos_cuota_id ON cuota_pagos(cuota_id);
CREATE INDEX idx_pagos_fecha ON pagos(fecha_pago);
CREATE INDEX idx_cuotas_fecha_vencimiento ON cuotas(fecha_vencimiento);
CREATE INDEX idx_cuota_pagos_fecha ON cuota_pagos(fecha_aplicacion);
*/
