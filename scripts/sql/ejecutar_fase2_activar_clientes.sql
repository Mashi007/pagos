-- ============================================================================
-- SCRIPT SQL: EJECUTAR FASE 2 - ACTIVAR CLIENTES INACTIVOS
-- Objetivo: Activar 182 clientes inactivos que tienen préstamos/pagos activos
-- Fecha: 2026-01-11
-- ============================================================================

-- ============================================================================
-- VERIFICACIÓN PREVIA: Ver cuántos clientes se activarían
-- ============================================================================
SELECT 
    'PRE-ACTIVACION: Clientes a activar' AS verificacion,
    COUNT(*) AS clientes_a_activar
FROM clientes c
WHERE c.cedula IN (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    LEFT JOIN clientes c2 ON p.cedula = c2.cedula AND c2.activo = TRUE
    WHERE c2.id IS NULL
)
AND c.activo = FALSE;

-- ============================================================================
-- VER DETALLES DE CLIENTES QUE SE ACTIVARÁN
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
    LEFT JOIN clientes c2 ON p2.cedula = c2.cedula AND c2.activo = TRUE
    WHERE c2.id IS NULL
)
AND c.activo = FALSE
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY c.cedula
LIMIT 20;

-- ============================================================================
-- EJECUTAR ACTIVACIÓN DE CLIENTES
-- ============================================================================
-- IMPORTANTE: Revisar los resultados anteriores antes de ejecutar
-- Descomentar para ejecutar:

/*
BEGIN;

WITH cedulas_problema AS (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
    WHERE c.id IS NULL
)
UPDATE clientes 
SET activo = TRUE, 
    fecha_actualizacion = CURRENT_TIMESTAMP,
    estado = 'ACTIVO'
WHERE cedula IN (SELECT cedula FROM cedulas_problema)
  AND activo = FALSE
RETURNING id, cedula, nombres, activo, estado;

COMMIT;
*/

-- ============================================================================
-- VERIFICACIÓN POSTERIOR: Confirmar que se activaron
-- ============================================================================
-- Ejecutar después de la activación:

/*
SELECT 
    'POST-ACTIVACION: Clientes activados' AS verificacion,
    COUNT(*) AS clientes_activados
FROM clientes c
WHERE c.cedula IN (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    LEFT JOIN clientes c2 ON p.cedula = c2.cedula AND c2.activo = TRUE
    WHERE c2.id IS NULL
)
AND c.activo = TRUE;

-- Verificar que no queden cédulas sin cliente activo
SELECT 
    'VERIFICACION FINAL: Cédulas en préstamos sin cliente activo' AS verificacion,
    COUNT(DISTINCT p.cedula) AS cedulas_sin_cliente_activo,
    CASE 
        WHEN COUNT(DISTINCT p.cedula) = 0 THEN 'OK: Todas las cédulas tienen cliente activo'
        ELSE 'ERROR: Aún existen cédulas sin cliente activo'
    END AS resultado
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
WHERE c.id IS NULL;
*/

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
