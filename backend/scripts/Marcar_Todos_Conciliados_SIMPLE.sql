-- ============================================
-- MARCAR TODOS LOS REGISTROS COMO CONCILIADOS
-- ============================================
-- Script simple para marcar todos los 238,304 registros como conciliados
-- ============================================

-- Verificar estado ANTES
SELECT 
    'ANTES' AS estado,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS no_conciliados
FROM pagos_staging;

-- ACTUALIZAR TODOS LOS REGISTROS
UPDATE pagos_staging
SET 
    conciliado = TRUE,
    fecha_conciliacion = COALESCE(
        NULLIF(fecha_conciliacion, ''),
        fecha_pago,
        TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
    )
WHERE TRUE;

-- Verificar estado DESPUÉS
SELECT 
    'DESPUÉS' AS estado,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS no_conciliados,
    ROUND(
        (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
        2
    ) AS porcentaje_conciliados
FROM pagos_staging;

-- Muestra de registros actualizados (primeros 10)
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    conciliado,
    fecha_conciliacion
FROM pagos_staging
ORDER BY id_stg DESC
LIMIT 10;

