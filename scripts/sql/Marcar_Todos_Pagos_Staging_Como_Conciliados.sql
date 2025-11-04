-- ============================================
-- MARCAR TODOS LOS PAGOS_STAGING COMO CONCILIADOS
-- ============================================
-- Este script marca todos los registros de la tabla 'pagos_staging' como conciliados.
-- Se ejecuta después de una migración de base de datos donde todos los pagos
-- históricos deben considerarse como conciliados.
-- 
-- ⚠️ IMPORTANTE: Este script requiere que la columna 'conciliado' exista en la tabla 'pagos_staging'.
-- Si no existe, ejecuta primero: Agregar_Columna_Conciliado_Pagos_Staging.sql
-- ============================================

-- PASO 0: Verificar que la columna 'conciliado' existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'pagos_staging' 
          AND column_name = 'conciliado'
    ) THEN
        RAISE EXCEPTION '❌ ERROR: La columna conciliado NO EXISTE en la tabla pagos_staging. Ejecuta primero: Agregar_Columna_Conciliado_Pagos_Staging.sql';
    END IF;
END $$;

-- PASO 1: Verificar estado actual ANTES de la actualización
SELECT 
    'ANTES DE LA ACTUALIZACIÓN' AS estado,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS registros_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS registros_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS registros_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL AND fecha_conciliacion != '' THEN 1 END) AS registros_con_fecha_conciliacion,
    COUNT(CASE WHEN fecha_conciliacion IS NULL OR fecha_conciliacion = '' THEN 1 END) AS registros_sin_fecha_conciliacion,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos_staging;

-- PASO 2: Mostrar muestra de registros antes de actualizar (opcional - descomentar si se necesita)
/*
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
*/

-- ============================================
-- ACTUALIZACIÓN PRINCIPAL
-- ============================================

-- PASO 3: Marcar TODOS los registros de pagos_staging como conciliados
-- Establece conciliado = TRUE y fecha_conciliacion = fecha_pago (o NOW() si no hay fecha_pago)
UPDATE pagos_staging
SET 
    conciliado = TRUE,
    fecha_conciliacion = COALESCE(
        NULLIF(fecha_conciliacion, ''),  -- Si ya tiene fecha y no está vacía, mantenerla
        fecha_pago,                      -- Si no, usar fecha_pago
        TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')  -- Si tampoco hay fecha_pago, usar fecha actual como TEXT
    )
WHERE TRUE;  -- Actualizar todos los registros

-- PASO 4: Verificar estado DESPUÉS de la actualización
SELECT 
    'DESPUÉS DE LA ACTUALIZACIÓN' AS estado,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS registros_conciliados,
    COUNT(CASE WHEN conciliado = FALSE THEN 1 END) AS registros_no_conciliados,
    COUNT(CASE WHEN conciliado IS NULL THEN 1 END) AS registros_con_conciliado_null,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL AND fecha_conciliacion != '' THEN 1 END) AS registros_con_fecha_conciliacion,
    COUNT(CASE WHEN fecha_conciliacion IS NULL OR fecha_conciliacion = '' THEN 1 END) AS registros_sin_fecha_conciliacion,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND(
                (COUNT(CASE WHEN conciliado = TRUE THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            )
        ELSE 0
    END AS porcentaje_conciliados
FROM pagos_staging;

-- PASO 5: Mostrar muestra de registros después de actualizar
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    conciliado,
    fecha_conciliacion,
    CASE 
        WHEN conciliado = TRUE THEN '✅ CONCILIADO'
        WHEN conciliado = FALSE THEN '❌ NO CONCILIADO'
        WHEN conciliado IS NULL THEN '⚠️ NULL'
        ELSE '❓ DESCONOCIDO'
    END AS estado_conciliacion
FROM pagos_staging
ORDER BY id_stg DESC
LIMIT 20;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '✅ ACTUALIZACIÓN COMPLETADA EN pagos_staging' AS mensaje,
    COUNT(*) AS total_registros_actualizados,
    COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS total_conciliados,
    COUNT(CASE WHEN fecha_conciliacion IS NOT NULL AND fecha_conciliacion != '' THEN 1 END) AS total_con_fecha_conciliacion,
    MIN(fecha_conciliacion) AS fecha_conciliacion_mas_antigua,
    MAX(fecha_conciliacion) AS fecha_conciliacion_mas_reciente
FROM pagos_staging
WHERE conciliado = TRUE;

-- ============================================
-- NOTAS IMPORTANTES
-- ============================================
-- 1. Este script actualiza TODOS los registros en pagos_staging
-- 2. Si un registro ya tiene fecha_conciliacion, se mantiene (no se sobrescribe)
-- 3. Si no tiene fecha_conciliacion, se usa fecha_pago o NOW()
-- 4. fecha_conciliacion se guarda como TEXT (por consistencia con fecha_pago que también es TEXT)
-- 5. Se recomienda hacer un BACKUP antes de ejecutar este script
-- 6. Este script es idempotente: se puede ejecutar múltiples veces sin problemas

