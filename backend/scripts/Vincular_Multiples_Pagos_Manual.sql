-- ============================================================================
-- VINCULAR MULTIPLES PAGOS MANUALMENTE
-- Script para vincular varios pagos de una vez usando una tabla de mapeo
-- ============================================================================

-- INSTRUCCIONES:
-- 1. Crear una tabla temporal con los mapeos pago_id -> prestamo_id
-- 2. Revisar los mapeos
-- 3. Ejecutar el UPDATE masivo

-- ============================================================================
-- PASO 1: Crear tabla temporal para mapeos
-- ============================================================================

CREATE TEMP TABLE mapeo_pagos_prestamos (
    pago_id INTEGER NOT NULL,
    prestamo_id INTEGER NOT NULL,
    cedula_cliente VARCHAR(20),
    monto_pagado NUMERIC(12,2),
    observaciones TEXT
);

-- ============================================================================
-- PASO 2: INSERTAR MAPEOS MANUALES (ejemplo - completar con los 249 casos)
-- ============================================================================

/*
-- FORMATO:
INSERT INTO mapeo_pagos_prestamos (pago_id, prestamo_id, cedula_cliente, monto_pagado, observaciones)
VALUES 
    (pago_id_1, prestamo_id_1, 'cedula_cliente', monto, 'Observacion'),
    (pago_id_2, prestamo_id_2, 'cedula_cliente', monto, 'Observacion'),
    -- ... agregar los 249 casos
    (pago_id_249, prestamo_id_249, 'cedula_cliente', monto, 'Observacion');
*/

-- ============================================================================
-- PASO 3: PREVIEW - Verificar mapeos antes de ejecutar
-- ============================================================================

SELECT 
    'PASO 3: Preview de mapeos' AS seccion;

SELECT 
    mpp.pago_id,
    mpp.prestamo_id,
    mpp.cedula_cliente,
    mpp.monto_pagado,
    mpp.observaciones,
    p.cedula_cliente AS cedula_actual_pago,
    pr.cedula AS cedula_prestamo,
    pr.estado AS estado_prestamo,
    CASE 
        WHEN p.cedula_cliente = pr.cedula AND pr.estado = 'APROBADO' THEN 'OK'
        ELSE 'ERROR: No coincide'
    END AS validacion
FROM mapeo_pagos_prestamos mpp
INNER JOIN pagos p ON mpp.pago_id = p.id
INNER JOIN prestamos pr ON mpp.prestamo_id = pr.id;

-- ============================================================================
-- PASO 4: ACTUALIZAR PAGOS (DESCOMENTAR PARA EJECUTAR)
-- ============================================================================

/*
UPDATE pagos p
SET prestamo_id = mpp.prestamo_id
FROM mapeo_pagos_prestamos mpp
WHERE p.id = mpp.pago_id
    AND EXISTS (
        SELECT 1 
        FROM prestamos pr 
        WHERE pr.id = mpp.prestamo_id 
            AND pr.cedula = p.cedula_cliente
            AND pr.estado = 'APROBADO'
    );
*/

-- ============================================================================
-- PASO 5: Verificar resultados
-- ============================================================================

SELECT 
    'PASO 5: Verificacion despues de actualizar' AS seccion;

SELECT 
    COUNT(*) AS total_actualizados,
    COUNT(DISTINCT prestamo_id) AS prestamos_vinculados
FROM pagos
WHERE id IN (SELECT pago_id FROM mapeo_pagos_prestamos)
    AND prestamo_id IS NOT NULL;

-- ============================================================================
-- PASO 6: Limpiar tabla temporal
-- ============================================================================

-- DROP TABLE mapeo_pagos_prestamos;

