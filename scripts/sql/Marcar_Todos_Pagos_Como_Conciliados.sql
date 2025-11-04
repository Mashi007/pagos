-- ============================================
-- MARCAR TODOS LOS PAGOS COMO CONCILIADOS
-- ============================================
-- Este script marca todos los registros de la tabla 'pagos' como conciliados.
-- Se ejecuta después de una migración de base de datos donde todos los pagos
-- históricos deben considerarse como conciliados.
-- ============================================

-- PASO 1: Verificar estado actual ANTES de la actualización
SELECT 
    'ANTES DE LA ACTUALIZACIÓN' AS estado,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS pagos_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL THEN 1 END) AS pagos_con_fecha_conciliacion,
    COUNT(CASE WHEN fecha_conciliacion IS NULL THEN 1 END) AS pagos_sin_fecha_conciliacion,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos
WHERE activo = TRUE;

-- PASO 2: Mostrar muestra de registros antes de actualizar (opcional - descomentar si se necesita)
/*
SELECT 
    id,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    conciliado,
    fecha_conciliacion,
    verificado_concordancia
FROM pagos
WHERE activo = TRUE
ORDER BY id DESC
LIMIT 10;
*/

-- ============================================
-- ACTUALIZACIÓN PRINCIPAL
-- ============================================

-- PASO 3: Marcar TODOS los pagos activos como conciliados
-- Establece conciliado = TRUE y fecha_conciliacion = fecha_pago (o NOW() si no hay fecha_pago)
UPDATE pagos
SET 
    conciliado = TRUE,
    fecha_conciliacion = COALESCE(
        fecha_conciliacion,  -- Si ya tiene fecha, mantenerla
        fecha_pago,          -- Si no, usar fecha_pago
        NOW()                -- Si tampoco hay fecha_pago, usar fecha actual
    ),
    verificado_concordancia = CASE 
        WHEN verificado_concordancia IS NULL OR verificado_concordancia = '' THEN 'SI'
        ELSE verificado_concordancia  -- Mantener el valor existente si ya está configurado
    END
WHERE activo = TRUE;

-- PASO 4: Verificar estado DESPUÉS de la actualización
SELECT 
    'DESPUÉS DE LA ACTUALIZACIÓN' AS estado,
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS pagos_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS pagos_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL THEN 1 END) AS pagos_con_fecha_conciliacion,
    COUNT(CASE WHEN fecha_conciliacion IS NULL THEN 1 END) AS pagos_sin_fecha_conciliacion,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos
WHERE activo = TRUE;

-- PASO 5: Mostrar muestra de registros después de actualizar
SELECT 
    id,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    conciliado,
    fecha_conciliacion,
    verificado_concordancia,
    CASE 
        WHEN conciliado = TRUE THEN '✅ CONCILIADO'
        WHEN conciliado = FALSE THEN '❌ NO CONCILIADO'
        WHEN conciliado IS NULL THEN '⚠️ NULL'
        ELSE '❓ DESCONOCIDO'
    END AS estado_conciliacion
FROM pagos
WHERE activo = TRUE
ORDER BY id DESC
LIMIT 20;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '✅ ACTUALIZACIÓN COMPLETADA' AS mensaje,
    COUNT(*) AS total_pagos_actualizados,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS total_conciliados,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL THEN 1 END) AS total_con_fecha_conciliacion,
    MIN(fecha_conciliacion) AS fecha_conciliacion_mas_antigua,
    MAX(fecha_conciliacion) AS fecha_conciliacion_mas_reciente
FROM pagos
WHERE activo = TRUE AND conciliado = TRUE;

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 1. Este script solo actualiza registros con activo = TRUE
-- 2. Si un registro ya tiene fecha_conciliacion, se mantiene (no se sobrescribe)
-- 3. Si no tiene fecha_conciliacion, se usa fecha_pago o NOW()
-- 4. verificado_concordancia se establece en 'SI' si está NULL o vacío
-- 5. Se recomienda hacer un BACKUP antes de ejecutar este script
-- 6. Este script es idempotente: se puede ejecutar múltiples veces sin problemas

