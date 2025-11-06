-- ================================================================
-- VERIFICACIÓN: Desglose de Cuotas por Estado de Pago
-- ================================================================
-- Este script muestra exactamente cuántas cuotas están:
-- 1. Pagadas (100%)
-- 2. Con pago parcial
-- 3. Sin pago
-- ================================================================

-- ================================================================
-- PASO 1: Desglose por categoría de pago
-- ================================================================
SELECT 
    CASE 
        WHEN total_pagado >= monto_cuota THEN '✅ PAGADAS (100%)'
        WHEN total_pagado > 0 THEN '⚠️ PAGO PARCIAL'
        ELSE '❌ SIN PAGO'
    END AS categoria,
    COUNT(*) AS cantidad_cuotas,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cuotas), 2) AS porcentaje,
    SUM(monto_cuota) AS total_monto_cuotas,
    SUM(total_pagado) AS total_pagado,
    ROUND(AVG(total_pagado * 100.0 / NULLIF(monto_cuota, 0)), 2) AS porcentaje_promedio_pagado
FROM cuotas
GROUP BY 
    CASE 
        WHEN total_pagado >= monto_cuota THEN '✅ PAGADAS (100%)'
        WHEN total_pagado > 0 THEN '⚠️ PAGO PARCIAL'
        ELSE '❌ SIN PAGO'
    END
ORDER BY cantidad_cuotas DESC;

-- ================================================================
-- PASO 2: Desglose por estado actual
-- ================================================================
SELECT 
    estado,
    COUNT(*) AS cantidad,
    COUNT(CASE WHEN total_pagado >= monto_cuota THEN 1 END) AS cuotas_completas,
    COUNT(CASE WHEN total_pagado > 0 AND total_pagado < monto_cuota THEN 1 END) AS cuotas_parciales,
    COUNT(CASE WHEN total_pagado = 0 THEN 1 END) AS cuotas_sin_pago,
    SUM(monto_cuota) AS total_monto,
    SUM(total_pagado) AS total_pagado
FROM cuotas
GROUP BY estado
ORDER BY cantidad DESC;

-- ================================================================
-- PASO 3: Resumen consolidado
-- ================================================================
SELECT 
    'RESUMEN CONSOLIDADO' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN total_pagado >= monto_cuota THEN 1 END) AS cuotas_100_pagadas,
    COUNT(CASE WHEN total_pagado > 0 AND total_pagado < monto_cuota THEN 1 END) AS cuotas_pago_parcial,
    COUNT(CASE WHEN total_pagado = 0 THEN 1 END) AS cuotas_sin_pago,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS estado_pagado,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS estado_pendiente,
    COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) AS estado_parcial
FROM cuotas;

-- ================================================================
-- PASO 4: Verificar coherencia estado vs total_pagado
-- ================================================================
SELECT 
    'COHERENCIA ESTADO VS PAGO' AS tipo,
    estado,
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'Completo (>=100%)'
        WHEN total_pagado > 0 THEN 'Parcial (>0% y <100%)'
        ELSE 'Sin pago (0%)'
    END AS categoria_pago,
    COUNT(*) AS cantidad
FROM cuotas
GROUP BY 
    estado,
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'Completo (>=100%)'
        WHEN total_pagado > 0 THEN 'Parcial (>0% y <100%)'
        ELSE 'Sin pago (0%)'
    END
ORDER BY estado, categoria_pago;

