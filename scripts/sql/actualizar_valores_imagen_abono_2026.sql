-- ============================================================================
-- ACTUALIZAR VALORES DE LA IMAGEN EN abono_2026
-- ============================================================================
-- Script para actualizar los valores de referencia (imagen) en abono_2026
-- 
-- Valores de la imagen proporcionada:
-- V14406409: 2350
-- V27223265: 864
-- V23681759: 1120
-- V23107415: 730
-- ============================================================================

-- ============================================================================
-- OPCIÓN 1: Actualizar valores específicos de la imagen
-- ============================================================================
-- Ejecuta este bloque para actualizar los 4 valores de la imagen
-- ============================================================================

-- Actualizar V14406409
UPDATE abono_2026 
SET abonos = 2350,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V14406409';

-- Actualizar V27223265
UPDATE abono_2026 
SET abonos = 864,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V27223265';

-- Actualizar V23681759
UPDATE abono_2026 
SET abonos = 1120,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V23681759';

-- Actualizar V23107415
UPDATE abono_2026 
SET abonos = 730,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V23107415';

-- ============================================================================
-- OPCIÓN 2: Insertar si no existen (usar si las cédulas no están en abono_2026)
-- ============================================================================
-- Descomenta este bloque si necesitas INSERTAR en lugar de UPDATE
-- ============================================================================

/*
-- Insertar V14406409 si no existe
INSERT INTO abono_2026 (cedula, abonos, fecha_creacion, fecha_actualizacion)
VALUES ('V14406409', 2350, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (cedula) DO UPDATE SET
    abonos = 2350,
    fecha_actualizacion = CURRENT_TIMESTAMP;

-- Insertar V27223265 si no existe
INSERT INTO abono_2026 (cedula, abonos, fecha_creacion, fecha_actualizacion)
VALUES ('V27223265', 864, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (cedula) DO UPDATE SET
    abonos = 864,
    fecha_actualizacion = CURRENT_TIMESTAMP;

-- Insertar V23681759 si no existe
INSERT INTO abono_2026 (cedula, abonos, fecha_creacion, fecha_actualizacion)
VALUES ('V23681759', 1120, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (cedula) DO UPDATE SET
    abonos = 1120,
    fecha_actualizacion = CURRENT_TIMESTAMP;

-- Insertar V23107415 si no existe
INSERT INTO abono_2026 (cedula, abonos, fecha_creacion, fecha_actualizacion)
VALUES ('V23107415', 730, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (cedula) DO UPDATE SET
    abonos = 730,
    fecha_actualizacion = CURRENT_TIMESTAMP;
*/

-- ============================================================================
-- VERIFICACIÓN: Ver los valores actualizados
-- ============================================================================

SELECT 
    cedula,
    abonos AS total_abonos_imagen,
    fecha_actualizacion
FROM abono_2026
WHERE cedula IN ('V14406409', 'V27223265', 'V23681759', 'V23107415')
ORDER BY cedula;

-- ============================================================================
-- COMPARAR CON BD: Ver diferencias después de actualizar
-- ============================================================================

WITH abonos_bd AS (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IN ('V14406409', 'V27223265', 'V23681759', 'V23107415')
      AND p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_imagen AS (
    SELECT 
        cedula,
        COALESCE(abonos::numeric, 0) AS total_abonos_imagen
    FROM abono_2026
    WHERE cedula IN ('V14406409', 'V27223265', 'V23681759', 'V23107415')
)
SELECT 
    COALESCE(bd.cedula, img.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS total_abonos_bd,
    COALESCE(img.total_abonos_imagen, 0) AS total_abonos_imagen,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) AS diferencia,
    CASE 
        WHEN bd.cedula IS NULL THEN '⚠️ No encontrada en BD'
        WHEN img.cedula IS NULL THEN '⚠️ No en imagen'
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) <= 0.01 THEN '✅ Coincide'
        ELSE '❌ Diferencia'
    END AS estado,
    CASE 
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) > 0.01 THEN
            CASE 
                WHEN COALESCE(bd.total_abonos_bd, 0) > COALESCE(img.total_abonos_imagen, 0) THEN 
                    'BD tiene ' || ROUND((COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0))::numeric, 2) || ' más'
                ELSE 
                    'Imagen tiene ' || ROUND((COALESCE(img.total_abonos_imagen, 0) - COALESCE(bd.total_abonos_bd, 0))::numeric, 2) || ' más'
            END
        ELSE ''
    END AS detalle
FROM abonos_bd bd
FULL OUTER JOIN abonos_imagen img ON bd.cedula = img.cedula
ORDER BY diferencia DESC, cedula;
