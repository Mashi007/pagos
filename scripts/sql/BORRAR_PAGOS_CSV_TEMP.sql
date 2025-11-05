-- ============================================================================
-- BORRAR TABLA TEMPORAL: pagos_csv_temp
-- ============================================================================
-- Esta tabla fue creada solo para la importación de CSV
-- Los 13,679 registros válidos ya están en la tabla 'pagos'
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR QUE LOS DATOS ESTÁN EN 'pagos' ANTES DE BORRAR
-- ============================================================================
SELECT 
    '=== VERIFICACIÓN PREVIA ===' AS verificacion,
    (SELECT COUNT(*) FROM pagos) AS registros_en_pagos,
    (SELECT COUNT(*) FROM pagos_csv_temp) AS registros_en_temp,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos) >= 13679 THEN 
            '✅ Datos están en pagos - Puedes borrar pagos_csv_temp'
        ELSE 
            '⚠️ Revisar: Menos registros de lo esperado en pagos'
    END AS estado;

-- ============================================================================
-- 2. BORRAR TABLA TEMPORAL
-- ============================================================================
-- ⚠️ EJECUTA ESTO SOLO DESPUÉS DE VERIFICAR QUE LOS DATOS ESTÁN EN 'pagos'
DROP TABLE IF EXISTS pagos_csv_temp CASCADE;

-- ============================================================================
-- 3. VERIFICAR QUE SE BORRÓ CORRECTAMENTE
-- ============================================================================
SELECT 
    '=== VERIFICACIÓN POST-BORRADO ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'pagos_csv_temp'
        ) THEN '❌ La tabla AÚN EXISTE'
        ELSE '✅ La tabla fue BORRADA correctamente'
    END AS estado;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

