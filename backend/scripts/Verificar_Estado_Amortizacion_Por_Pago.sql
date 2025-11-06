-- ================================================================
-- VERIFICACIÓN: Estado de Amortización y Actualización por Pago
-- ================================================================
-- Este script verifica:
-- 1. Si la tabla de amortización (cuotas) está activa y tiene datos
-- 2. Cómo se actualiza el estado de las cuotas cuando se aplica un pago
-- 3. Relación entre pagos y cuotas
-- ================================================================

-- ================================================================
-- PASO 1: Verificar estructura y existencia de tabla cuotas
-- ================================================================
SELECT 
    'PASO 1: Verificación de tabla cuotas' AS paso,
    COUNT(*) AS total_cuotas,
    COUNT(DISTINCT prestamo_id) AS total_prestamos_con_cuotas,
    MIN(fecha_vencimiento) AS primera_cuota_vencimiento,
    MAX(fecha_vencimiento) AS ultima_cuota_vencimiento
FROM cuotas;

-- ================================================================
-- PASO 2: Distribución de estados de cuotas
-- ================================================================
SELECT 
    'PASO 2: Distribución de estados' AS paso,
    estado,
    COUNT(*) AS cantidad_cuotas,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cuotas), 2) AS porcentaje,
    SUM(monto_cuota) AS total_monto_cuotas,
    SUM(total_pagado) AS total_pagado,
    SUM(monto_cuota - total_pagado) AS total_pendiente
FROM cuotas
GROUP BY estado
ORDER BY cantidad_cuotas DESC;

-- ================================================================
-- PASO 3: Verificar relación entre pagos y cuotas
-- ================================================================
SELECT 
    'PASO 3: Relación pagos-cuotas' AS paso,
    COUNT(DISTINCT pago_id) AS total_pagos_con_cuotas,
    COUNT(DISTINCT cuota_id) AS total_cuotas_con_pagos,
    SUM(monto_aplicado) AS total_monto_aplicado,
    SUM(aplicado_a_capital) AS total_aplicado_capital,
    SUM(aplicado_a_interes) AS total_aplicado_interes,
    SUM(aplicado_a_mora) AS total_aplicado_mora
FROM pago_cuotas;

-- ================================================================
-- PASO 4: Verificar actualización de estado por pago
-- ================================================================
-- Cuotas que tienen pagos pero estado no es PAGADO (deberían estar PAGADO si total_pagado >= monto_cuota)
SELECT 
    'PASO 4: Cuotas con pagos pero estado incorrecto' AS paso,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.estado AS estado_actual,
    c.monto_cuota,
    c.total_pagado,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'DEBERÍA SER PAGADO'
        WHEN c.total_pagado > 0 THEN 'DEBERÍA SER PARCIAL/PENDIENTE'
        ELSE 'DEBERÍA SER PENDIENTE'
    END AS estado_esperado,
    c.fecha_vencimiento,
    c.fecha_pago,
    (SELECT COUNT(*) FROM pago_cuotas pc WHERE pc.cuota_id = c.id) AS cantidad_pagos_aplicados
FROM cuotas c
WHERE c.total_pagado > 0
  AND (
    -- Estado incorrecto: total_pagado >= monto_cuota pero estado no es PAGADO
    (c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO')
    OR
    -- Estado incorrecto: total_pagado < monto_cuota pero estado es PAGADO
    (c.total_pagado < c.monto_cuota AND c.estado = 'PAGADO')
  )
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- ================================================================
-- PASO 5: Verificar flujo de actualización reciente
-- ================================================================
-- Últimos 10 pagos y su impacto en cuotas
SELECT 
    'PASO 5: Últimos pagos y cuotas afectadas' AS paso,
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.fecha_pago,
    c.id AS cuota_id,
    c.numero_cuota,
    c.estado AS estado_cuota,
    c.monto_cuota,
    c.total_pagado AS total_pagado_cuota,
    pc.monto_aplicado AS monto_aplicado_desde_pago,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN '✅ COMPLETO'
        WHEN c.total_pagado > 0 THEN '⚠️ PARCIAL'
        ELSE '❌ PENDIENTE'
    END AS estado_verificacion
FROM pagos p
INNER JOIN pago_cuotas pc ON pc.pago_id = p.id
INNER JOIN cuotas c ON c.id = pc.cuota_id
ORDER BY p.fecha_pago DESC, p.id DESC
LIMIT 20;

-- ================================================================
-- PASO 6: Verificar cuotas con pagos parciales
-- ================================================================
SELECT 
    'PASO 6: Cuotas con pagos parciales' AS paso,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.estado,
    c.monto_cuota,
    c.total_pagado,
    ROUND((c.total_pagado * 100.0 / NULLIF(c.monto_cuota, 0)), 2) AS porcentaje_pagado,
    c.monto_cuota - c.total_pagado AS monto_pendiente,
    c.fecha_vencimiento,
    CASE 
        WHEN c.fecha_vencimiento < CURRENT_DATE THEN 'VENCIDA'
        ELSE 'VIGENTE'
    END AS estado_vencimiento,
    (SELECT COUNT(*) FROM pago_cuotas pc WHERE pc.cuota_id = c.id) AS cantidad_pagos
FROM cuotas c
WHERE c.total_pagado > 0 
  AND c.total_pagado < c.monto_cuota
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- ================================================================
-- PASO 7: Verificar que todas las cuotas PAGADAS tienen fecha_pago
-- ================================================================
SELECT 
    'PASO 7: Cuotas PAGADAS sin fecha_pago' AS paso,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.estado,
    c.monto_cuota,
    c.total_pagado,
    c.fecha_pago,
    c.fecha_vencimiento
FROM cuotas c
WHERE c.estado = 'PAGADO'
  AND c.fecha_pago IS NULL
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- ================================================================
-- PASO 8: Resumen de coherencia estado vs total_pagado
-- ================================================================
SELECT 
    'PASO 8: Resumen coherencia estado' AS paso,
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'COMPLETO (>=100%)'
        WHEN total_pagado > 0 THEN 'PARCIAL (>0% y <100%)'
        ELSE 'SIN PAGO (0%)'
    END AS categoria_pago,
    estado,
    COUNT(*) AS cantidad,
    SUM(monto_cuota) AS total_monto_cuotas,
    SUM(total_pagado) AS total_pagado_sum,
    ROUND(AVG(total_pagado * 100.0 / NULLIF(monto_cuota, 0)), 2) AS porcentaje_promedio
FROM cuotas
GROUP BY 
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'COMPLETO (>=100%)'
        WHEN total_pagado > 0 THEN 'PARCIAL (>0% y <100%)'
        ELSE 'SIN PAGO (0%)'
    END,
    estado
ORDER BY categoria_pago, estado;

-- ================================================================
-- PASO 9: Verificar que las cuotas se actualizan correctamente
-- ================================================================
-- Comparar: total_pagado debe ser igual a la suma de monto_aplicado en pago_cuotas
SELECT 
    'PASO 9: Verificación suma pagos vs total_pagado' AS paso,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.total_pagado AS total_pagado_en_cuota,
    COALESCE(SUM(pc.monto_aplicado), 0) AS suma_monto_aplicado_pago_cuotas,
    c.total_pagado - COALESCE(SUM(pc.monto_aplicado), 0) AS diferencia,
    CASE 
        WHEN ABS(c.total_pagado - COALESCE(SUM(pc.monto_aplicado), 0)) > 0.01 THEN '❌ INCONSISTENCIA'
        ELSE '✅ COHERENTE'
    END AS estado_verificacion
FROM cuotas c
LEFT JOIN pago_cuotas pc ON pc.cuota_id = c.id
WHERE c.total_pagado > 0
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.total_pagado
HAVING ABS(c.total_pagado - COALESCE(SUM(pc.monto_aplicado), 0)) > 0.01
ORDER BY ABS(c.total_pagado - COALESCE(SUM(pc.monto_aplicado), 0)) DESC
LIMIT 20;

-- ================================================================
-- PASO 10: Verificar que la tabla está activa (tiene datos recientes)
-- ================================================================
SELECT 
    'PASO 10: Actividad reciente de tabla cuotas' AS paso,
    COUNT(*) AS total_cuotas,
    COUNT(DISTINCT prestamo_id) AS total_prestamos,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) AS cuotas_parciales,
    COUNT(CASE WHEN estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS cuotas_con_fecha_pago,
    MAX(fecha_pago) AS ultima_fecha_pago_registrada,
    MAX(fecha_vencimiento) AS ultima_fecha_vencimiento
FROM cuotas;

