-- ============================================================================
-- SCRIPT SQL: FASE 2 - SECUENCIA COMPLETA PARA DBEAVER
-- Objetivo: Activar 182 clientes inactivos que tienen préstamos/pagos activos
-- Fecha: 2026-01-11
-- ============================================================================
-- INSTRUCCIONES:
-- 1. Ejecutar cada sección por separado en DBeaver
-- 2. Revisar resultados antes de continuar
-- 3. Escribir "FIN" después de cada sección antes de continuar
-- ============================================================================

-- ============================================================================
-- PASO 0: DIAGNÓSTICO - Verificar estado actual
-- ============================================================================
-- Ejecutar esta consulta primero para diagnosticar el problema
-- ============================================================================

SELECT 
    'PASO 0: Diagnóstico' AS paso,
    COUNT(DISTINCT p.cedula) AS cedulas_en_prestamos_sin_cliente_activo,
    COUNT(DISTINCT c_inactivos.id) AS clientes_inactivos_con_esas_cedulas,
    COUNT(DISTINCT c_activos.id) AS clientes_activos_con_esas_cedulas
FROM prestamos p
LEFT JOIN clientes c_activos ON p.cedula = c_activos.cedula AND c_activos.activo = TRUE
LEFT JOIN clientes c_inactivos ON p.cedula = c_inactivos.cedula AND c_inactivos.activo = FALSE
WHERE c_activos.id IS NULL;

-- ============================================================================
-- PASO 1: VERIFICACIÓN PREVIA - Clientes a activar
-- ============================================================================
-- Ejecutar esta consulta para ver cuántos clientes se activarían
-- NOTA: Esta consulta cuenta DISTINCT por cédula para evitar duplicados
-- ============================================================================

SELECT 
    'PASO 1: Clientes a activar' AS paso,
    COUNT(DISTINCT c.cedula) AS clientes_a_activar,
    COUNT(*) AS registros_clientes_inactivos,
    'Revisar resultado antes de continuar' AS instruccion
FROM clientes c
WHERE c.cedula IN (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    WHERE NOT EXISTS (
        SELECT 1 
        FROM clientes c2 
        WHERE c2.cedula = p.cedula 
        AND c2.activo = TRUE
    )
)
AND c.activo = FALSE;

-- ============================================================================
-- PASO 2A: DIAGNÓSTICO DETALLADO - Ver qué cédulas tienen problema
-- ============================================================================
-- Ejecutar esta consulta para ver las primeras 10 cédulas con problema
-- ============================================================================

SELECT 
    'PASO 2A: Cédulas con problema' AS paso,
    p.cedula,
    COUNT(DISTINCT p.id) AS cantidad_prestamos,
    COUNT(DISTINCT c_activos.id) AS tiene_cliente_activo,
    COUNT(DISTINCT c_inactivos.id) AS tiene_cliente_inactivo,
    STRING_AGG(DISTINCT c_inactivos.estado, ', ') AS estados_clientes_inactivos
FROM prestamos p
LEFT JOIN clientes c_activos ON p.cedula = c_activos.cedula AND c_activos.activo = TRUE
LEFT JOIN clientes c_inactivos ON p.cedula = c_inactivos.cedula AND c_inactivos.activo = FALSE
WHERE c_activos.id IS NULL
GROUP BY p.cedula
ORDER BY cantidad_prestamos DESC
LIMIT 10;

-- ============================================================================
-- PASO 2: VER DETALLES DE CLIENTES QUE SE ACTIVARÁN (Primeros 20)
-- ============================================================================
-- Ejecutar esta consulta para ver detalles de los clientes
-- NOTA: Si esta consulta no devuelve resultados, significa que:
-- 1. Los clientes ya fueron activados, O
-- 2. No hay clientes inactivos con esas cédulas
-- ============================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS cantidad_prestamos,
    COUNT(DISTINCT pag.id) AS cantidad_pagos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN pagos pag ON c.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.cedula IN (
    SELECT DISTINCT p2.cedula
    FROM prestamos p2
    WHERE NOT EXISTS (
        SELECT 1 
        FROM clientes c2 
        WHERE c2.cedula = p2.cedula 
        AND c2.activo = TRUE
    )
)
AND c.activo = FALSE
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY c.cedula
LIMIT 20;

-- ============================================================================
-- PASO 3: VERIFICAR ESTADO ACTUAL DE CÉDULAS SIN CLIENTE ACTIVO
-- ============================================================================
-- Ejecutar esta consulta para ver el estado actual del problema
-- ============================================================================

SELECT 
    'PASO 3: Estado actual' AS paso,
    COUNT(DISTINCT p.cedula) AS cedulas_en_prestamos_sin_cliente_activo,
    COUNT(DISTINCT pag.cedula) AS cedulas_en_pagos_sin_cliente_activo,
    COUNT(DISTINCT pag.id) AS total_pagos_afectados,
    SUM(pag.monto_pagado) AS monto_total_afectado,
    CASE 
        WHEN COUNT(DISTINCT p.cedula) = 0 THEN '✅ PROBLEMA RESUELTO: Todos los clientes están activos'
        ELSE '⚠️ PROBLEMA PENDIENTE: Existen ' || COUNT(DISTINCT p.cedula) || ' cédulas sin cliente activo'
    END AS estado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.id IS NULL;

-- ============================================================================
-- VERIFICACIÓN: ¿El problema ya fue resuelto?
-- ============================================================================
-- Si el PASO 3 muestra 0 en todos los campos, significa que:
-- ✅ Los clientes ya fueron activados previamente
-- ✅ NO es necesario ejecutar el PASO 4
-- ✅ Puedes saltar directamente al PASO 6 para verificar
-- ============================================================================

SELECT 
    'VERIFICACIÓN PRE-ACTIVACIÓN' AS paso,
    CASE 
        WHEN (
            SELECT COUNT(DISTINCT p.cedula)
            FROM prestamos p
            LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
            WHERE c.id IS NULL
        ) = 0 
        THEN '✅ NO ES NECESARIO EJECUTAR PASO 4: El problema ya fue resuelto'
        ELSE '⚠️ EJECUTAR PASO 4: Aún hay clientes que necesitan activarse'
    END AS recomendacion;

-- ============================================================================
-- PAUSA: NO PROCESAR HASTA QUE NO SE ESCRIBA "FIN"
-- ============================================================================
-- Revisar todos los resultados anteriores
-- Si el PASO 3 muestra 0 en todos los campos, NO ejecutar el PASO 4
-- Si el PASO 3 muestra números > 0, entonces ejecutar el PASO 4
-- ============================================================================

-- ============================================================================
-- PASO 4: EJECUTAR ACTIVACIÓN DE CLIENTES
-- ============================================================================
-- IMPORTANTE: Solo ejecutar después de revisar los pasos anteriores
-- Este paso activará los 182 clientes inactivos
-- ============================================================================

BEGIN;

WITH cedulas_problema AS (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    WHERE NOT EXISTS (
        SELECT 1 
        FROM clientes c 
        WHERE c.cedula = p.cedula 
        AND c.activo = TRUE
    )
)
UPDATE clientes 
SET activo = TRUE, 
    fecha_actualizacion = CURRENT_TIMESTAMP,
    estado = 'ACTIVO'
WHERE cedula IN (SELECT cedula FROM cedulas_problema)
  AND activo = FALSE
RETURNING id, cedula, nombres, activo, estado;

COMMIT;

-- ============================================================================
-- PASO 5: VERIFICACIÓN POSTERIOR - Confirmar activación
-- ============================================================================
-- Ejecutar esta consulta después del PASO 4 para confirmar
-- ============================================================================

SELECT 
    'PASO 5: Verificación post-activación' AS paso,
    COUNT(DISTINCT c.cedula) AS clientes_activados,
    CASE 
        WHEN COUNT(DISTINCT c.cedula) = 182 THEN '✅ OK: Se activaron 182 clientes'
        WHEN COUNT(DISTINCT c.cedula) = 0 AND (
            SELECT COUNT(DISTINCT p.cedula)
            FROM prestamos p
            LEFT JOIN clientes c2 ON p.cedula = c2.cedula AND c2.activo = TRUE
            WHERE c2.id IS NULL
        ) = 0 THEN '✅ OK: No se activaron clientes porque el problema ya estaba resuelto'
        ELSE '⚠️ ADVERTENCIA: Se activaron ' || COUNT(DISTINCT c.cedula) || ' clientes (esperado: 182)'
    END AS resultado
FROM clientes c
WHERE c.cedula IN (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    WHERE NOT EXISTS (
        SELECT 1 
        FROM clientes c2 
        WHERE c2.cedula = p.cedula 
        AND c2.activo = TRUE
    )
)
AND c.activo = TRUE;

-- ============================================================================
-- PASO 6: VERIFICACIÓN FINAL - Cédulas sin cliente activo
-- ============================================================================
-- Esta consulta debe mostrar 0 cédulas sin cliente activo
-- ============================================================================

SELECT 
    'PASO 6: Verificación final' AS paso,
    COUNT(DISTINCT p.cedula) AS cedulas_en_prestamos_sin_cliente_activo,
    CASE 
        WHEN COUNT(DISTINCT p.cedula) = 0 THEN 'OK: Todas las cédulas tienen cliente activo'
        ELSE 'ERROR: Aún existen ' || COUNT(DISTINCT p.cedula) || ' cédulas sin cliente activo'
    END AS resultado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
WHERE c.id IS NULL;

-- ============================================================================
-- PASO 7: VERIFICACIÓN FINAL - Pagos sin cliente activo
-- ============================================================================
-- Esta consulta debe mostrar 0 cédulas en pagos sin cliente activo
-- ============================================================================

SELECT 
    'PASO 7: Verificación pagos' AS paso,
    COUNT(DISTINCT pag.cedula) AS cedulas_en_pagos_sin_cliente_activo,
    COUNT(DISTINCT pag.id) AS total_pagos_afectados,
    CASE 
        WHEN COUNT(DISTINCT pag.cedula) = 0 THEN 'OK: Todas las cédulas en pagos tienen cliente activo'
        ELSE 'ERROR: Aún existen ' || COUNT(DISTINCT pag.cedula) || ' cédulas en pagos sin cliente activo'
    END AS resultado
FROM pagos pag
LEFT JOIN clientes c ON pag.cedula = c.cedula AND c.activo = TRUE
WHERE pag.activo = TRUE AND c.id IS NULL;

-- ============================================================================
-- PASO 8: RESUMEN FINAL
-- ============================================================================
-- Ejecutar esta consulta para ver el resumen completo
-- ============================================================================

SELECT 
    'RESUMEN FINAL' AS tipo,
    'Cédulas en préstamos sin cliente activo' AS verificacion,
    COUNT(DISTINCT p.cedula)::text AS valor,
    CASE WHEN COUNT(DISTINCT p.cedula) = 0 THEN 'OK' ELSE 'ERROR' END AS estado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
WHERE c.id IS NULL

UNION ALL

SELECT 
    'RESUMEN FINAL',
    'Cédulas en pagos sin cliente activo',
    COUNT(DISTINCT pag.cedula)::text,
    CASE WHEN COUNT(DISTINCT pag.cedula) = 0 THEN 'OK' ELSE 'ERROR' END
FROM pagos pag
LEFT JOIN clientes c ON pag.cedula = c.cedula AND c.activo = TRUE
WHERE pag.activo = TRUE AND c.id IS NULL

UNION ALL

SELECT 
    'RESUMEN FINAL',
    'Total préstamos',
    COUNT(*)::text,
    'INFO'
FROM prestamos

UNION ALL

SELECT 
    'RESUMEN FINAL',
    'Préstamos con cliente activo',
    COUNT(DISTINCT p.id)::text,
    'INFO'
FROM prestamos p
INNER JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE

UNION ALL

SELECT 
    'RESUMEN FINAL',
    'Total pagos activos',
    COUNT(*)::text,
    'INFO'
FROM pagos
WHERE activo = TRUE

UNION ALL

SELECT 
    'RESUMEN FINAL',
    'Pagos activos con cliente activo',
    COUNT(DISTINCT pag.id)::text,
    'INFO'
FROM pagos pag
INNER JOIN clientes c ON pag.cedula = c.cedula AND c.activo = TRUE
WHERE pag.activo = TRUE;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
