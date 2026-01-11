-- ============================================================================
-- COMPARACIÓN DE ABONOS: BD vs VALORES DE LA IMAGEN
-- ============================================================================
-- Script para verificar los valores de abonos en BD y compararlos
-- con los valores mostrados en la imagen proporcionada
-- Solo muestra las cédulas con discrepancias
-- ============================================================================

WITH abonos_bd AS (
    -- Calcular abonos desde BD (suma de cuotas.total_pagado por cédula)
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IN (
        'V14406409', 'V27223265', 'V23681759', 'V23107415'
    )
      AND p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
valores_imagen AS (
    -- Valores de la imagen proporcionada
    SELECT 'V14406409' AS cedula, 2350::numeric AS total_abonos_imagen UNION ALL
    SELECT 'V27223265', 864 UNION ALL
    SELECT 'V23681759', 1120 UNION ALL
    SELECT 'V23107415', 730
)
SELECT 
    COALESCE(bd.cedula, img.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS total_abonos_bd,
    COALESCE(img.total_abonos_imagen, 0) AS total_abonos_imagen,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) AS diferencia,
    CASE 
        WHEN COALESCE(bd.total_abonos_bd, 0) > COALESCE(img.total_abonos_imagen, 0) THEN 
            'BD tiene ' || ROUND((COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0))::numeric, 2) || ' más'
        ELSE 
            'Imagen tiene ' || ROUND((COALESCE(img.total_abonos_imagen, 0) - COALESCE(bd.total_abonos_bd, 0))::numeric, 2) || ' más'
    END AS detalle
FROM abonos_bd bd
FULL OUTER JOIN valores_imagen img ON bd.cedula = img.cedula
WHERE ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(img.total_abonos_imagen, 0)) > 0.01
ORDER BY diferencia DESC;
