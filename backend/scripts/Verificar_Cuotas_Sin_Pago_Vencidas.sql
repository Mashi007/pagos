-- ================================================================
-- VERIFICACIÓN: Cuotas Sin Pago - ¿Vencidas o No Vencidas?
-- ================================================================
-- Este script muestra cuántas cuotas sin pago están vencidas
-- y cuántas aún no vencen (son normales)
-- ================================================================

-- ================================================================
-- PASO 1: Desglose de cuotas sin pago por estado de vencimiento
-- ================================================================
SELECT 
    CASE 
        WHEN fecha_vencimiento < CURRENT_DATE THEN '⚠️ VENCIDAS (EN MORA)'
        WHEN fecha_vencimiento >= CURRENT_DATE THEN '✅ NO VENCIDAS (NORMAL)'
        WHEN fecha_vencimiento IS NULL THEN '❓ SIN FECHA'
        ELSE '❓ OTRO'
    END AS estado_vencimiento,
    COUNT(*) AS cantidad_cuotas,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cuotas WHERE total_pagado = 0), 2) AS porcentaje,
    MIN(fecha_vencimiento) AS primera_fecha,
    MAX(fecha_vencimiento) AS ultima_fecha,
    SUM(monto_cuota) AS total_monto_pendiente
FROM cuotas
WHERE total_pagado = 0
GROUP BY 
    CASE 
        WHEN fecha_vencimiento < CURRENT_DATE THEN '⚠️ VENCIDAS (EN MORA)'
        WHEN fecha_vencimiento >= CURRENT_DATE THEN '✅ NO VENCIDAS (NORMAL)'
        WHEN fecha_vencimiento IS NULL THEN '❓ SIN FECHA'
        ELSE '❓ OTRO'
    END
ORDER BY cantidad_cuotas DESC;

-- ================================================================
-- PASO 2: Detalle de cuotas vencidas sin pago (MORA)
-- ================================================================
SELECT 
    'CUOTAS EN MORA' AS tipo,
    COUNT(*) AS total_cuotas_vencidas,
    COUNT(DISTINCT prestamo_id) AS total_prestamos_afectados,
    SUM(monto_cuota) AS total_monto_mora,
    AVG(CURRENT_DATE - fecha_vencimiento) AS dias_mora_promedio,
    MAX(CURRENT_DATE - fecha_vencimiento) AS dias_mora_maximo
FROM cuotas
WHERE total_pagado = 0
  AND fecha_vencimiento < CURRENT_DATE;

-- ================================================================
-- PASO 3: Detalle de cuotas no vencidas sin pago (NORMAL)
-- ================================================================
SELECT 
    'CUOTAS FUTURAS (NORMAL)' AS tipo,
    COUNT(*) AS total_cuotas_futuras,
    COUNT(DISTINCT prestamo_id) AS total_prestamos,
    SUM(monto_cuota) AS total_monto_futuro,
    MIN(fecha_vencimiento) AS proxima_cuota_vencer,
    MAX(fecha_vencimiento) AS ultima_cuota_vencer
FROM cuotas
WHERE total_pagado = 0
  AND fecha_vencimiento >= CURRENT_DATE;

-- ================================================================
-- PASO 4: Resumen consolidado
-- ================================================================
SELECT 
    'RESUMEN CONSOLIDADO' AS tipo,
    COUNT(*) AS total_cuotas_sin_pago,
    COUNT(CASE WHEN fecha_vencimiento < CURRENT_DATE THEN 1 END) AS cuotas_vencidas_mora,
    COUNT(CASE WHEN fecha_vencimiento >= CURRENT_DATE THEN 1 END) AS cuotas_futuras_normales,
    COUNT(CASE WHEN fecha_vencimiento IS NULL THEN 1 END) AS cuotas_sin_fecha,
    ROUND(COUNT(CASE WHEN fecha_vencimiento < CURRENT_DATE THEN 1 END) * 100.0 / COUNT(*), 2) AS porcentaje_mora,
    SUM(monto_cuota) AS total_monto_pendiente
FROM cuotas
WHERE total_pagado = 0;

-- ================================================================
-- PASO 5: Top 10 préstamos con más cuotas en mora
-- ================================================================
SELECT 
    prestamo_id,
    COUNT(*) AS cuotas_vencidas,
    SUM(monto_cuota) AS total_monto_mora,
    AVG(CURRENT_DATE - fecha_vencimiento) AS dias_mora_promedio,
    MIN(fecha_vencimiento) AS primera_cuota_vencida,
    MAX(fecha_vencimiento) AS ultima_cuota_vencida
FROM cuotas
WHERE total_pagado = 0
  AND fecha_vencimiento < CURRENT_DATE
GROUP BY prestamo_id
ORDER BY cuotas_vencidas DESC, total_monto_mora DESC
LIMIT 10;

